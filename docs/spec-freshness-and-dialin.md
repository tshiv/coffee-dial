# Spec — Freshness windows, one-lever dial-in, Aiden profile cleanup

Status: Steps 1-3 built and tested 2026-09-03. Step 4 (Aiden delete) still proposed — held for sign-off.

## What we're building

Three additions to the existing deterministic engine, in dependency order:

1. **Freshness windows** — a bag has a roast date; the engine computes when it is
   resting, ready, and tired, from roast level + process + decaf status.
2. **One-lever dial-in** — when a brew is rated, change exactly one variable for
   the next attempt and say why, chaining v1 → v2 → v3 per coffee.
3. **Aiden profile cleanup** — list and delete profiles on the brewer, so the
   dial-in chain doesn't fill the machine with junk.

**Who this is NOT for:** anyone but you. No accounts, no multi-user, no shared
catalog, no community voting. The competitor's moat is a 1,600-coffee communal
database; a catalog of one needs none of that machinery. Nothing here syncs
anywhere or requires a login beyond the Fellow credentials already in
`settings.json`.

**Explicitly out of scope for this spec:** Bottomless ingest and phone/camera
capture. See "Deferred" at the bottom.

---

## Step 1 — Bags and roast dates

**What:** A `bags` table. A bag is a coffee you own, with a roast date, an
optional open date, and an optional freeze/thaw pair. Brews reference a bag.

Freshness math is **gated on a real roast date** — no estimates. A bag without
one is in state `awaiting_roast_date`, and the UI shows a prompt to enter it
rather than a fabricated window.

**Files:**
- `backend/app.py` — modified: new `bags` table in `init_db()`, plus
  `_migrate_brews()` gaining a nullable `bag_id` column
- `backend/engine/freshness.py` — **created**
- `backend/app.py` — modified: `GET/POST/PUT /api/bags`, `DELETE /api/bags/<id>`

**Key decision:** Roast date is required rather than estimated from an order or
purchase date. Rejected the estimate-with-a-flag alternative — a freshness claim
is only worth making if the input is real, and every bag has the date printed on
it. Cost: the feature does nothing until you type six characters.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS bags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    coffee_name TEXT NOT NULL,
    roaster     TEXT,
    roast       TEXT,          -- light | medium | dark
    origin      TEXT,
    process     TEXT,
    is_decaf    INTEGER DEFAULT 0,
    storage     TEXT DEFAULT 'vacuum',  -- bag_ambient | airtight | vacuum
    roast_date  INTEGER,       -- epoch; NULL = awaiting_roast_date
    opened_at   INTEGER,       -- epoch; NULL = sealed
    frozen_at   INTEGER,
    thawed_at   INTEGER,
    finished_at INTEGER,
    notes       TEXT,
    created_at  INTEGER NOT NULL
);
```

**How it gets proven:**
```bash
curl -s -X POST localhost:8765/api/bags -H 'Content-Type: application/json' \
  -d '{"coffee_name":"Rwanda - Gasharu Honey","roast":"light","process":"honey","roast_date":1788000000}'
curl -s localhost:8765/api/bags | python3 -m json.tool
```
Expect the bag back with a computed `phase` and a `ready_range`. A second POST
with `roast_date` omitted must come back `phase: "awaiting_roast_date"` and
**no** window numbers.

---

## Step 2 — The freshness curve

**What:** Pure functions mapping bag attributes → phase boundaries. No I/O, no AI.

Rules, all overridable in one constants block:

| Input | Effect on rest period |
|---|---|
| Dark roast | ready ~2–5 days |
| Medium roast | ready ~5–12 days |
| Light roast | ready ~10–20 days |
| Natural / anaerobic / fermented process | +3 days to both bounds |
| Decaf | tired arrives ~30% sooner |

Two clocks, and the shorter one wins:
- **Sealed clock** — days since roast, driving rest → ready → tired
- **Open clock** — once opened, ~21 days of good drinking regardless of the
  sealed date, because oxygen is the dominant staling factor

Freezing **pauses both clocks**: a bag frozen on day 20 thaws on day 20.
Effective age = `(frozen_at - roast_date) + (now - thawed_at)` when a
freeze/thaw pair exists.

**Storage multiplies the open clock only.** Oxygen is the dominant staling
driver once air is in, so reducing its partial pressure slows staling. Degassing
is CO2 leaving the bean and is unaffected by the container — so storage must
**not** touch the rest period.

| `storage` | Open clock | Notes |
|---|---|---|
| `bag_ambient` | 21 × 0.8 ≈ 17 days | original bag, rolled shut |
| `airtight` | 21 days — baseline | sealed canister, no vacuum |
| `vacuum` | 21 × 1.5 ≈ 31 days | Fellow Atmos or equivalent, **re-pumped at every use** |

The 1.5 multiplier is a **convention derived from a vendor claim** ("up to 50%
longer"), not an independent measurement. The published research on vacuum
storage covers green beans and unopened packaging over months, which is not this
use case. Treat 1.5 as a starting guess to be corrected by actual ratings, and
keep it in the same overridable constants block as everything else.

Caveat worth encoding in the UI copy: Fellow's own FAQ states the canister holds
its seal roughly 3–4 days and advises re-twisting every 4–5 days. The `vacuum`
multiplier therefore assumes the vacuum is re-established each time the canister
is closed. A canister pumped once and left for a week behaves closer to
`airtight`, and the tooltip should say so rather than silently granting the bonus.

**Files:**
- `backend/engine/freshness.py` — created: `compute_phase()`,
  `effective_age_days()`, `ready_range()`
- `backend/tests/test_freshness.py` — **created**

**Key decision:** `ready` is returned as a **range** ("about 10–20 days"), not a
single day. Rejected a precise ready-date because roasters disagree with each
other about resting more than roast levels differ from one another — a point
estimate would be false precision. When roast level is unknown the function
assumes medium and sets `assumed_roast: true` in the response rather than
guessing silently.

**How it gets proven:** Unit tests, no server needed:
```bash
backend/venv/bin/python -m pytest backend/tests/test_freshness.py -v
```
Cases that must pass: light natural rests longer than dark washed; a bag frozen
mid-rest thaws mid-rest and finishes resting on the counter; an opened bag on
day 3 goes tired before a sealed bag of the same coffee; decaf tires early;
clearing a freeze restores the plain sealed-clock age.

Storage cases specifically: `vacuum` and `airtight` bags with identical roast
dates must produce an **identical `ready_range`** — storage must not leak into
the rest period — but a **different tired date**. Assert both in one test; that
pairing is the entire point of the split.

---

## Step 3 — One-lever dial-in

**What:** Rate a brew, get exactly one change for the next one, with a plain
sentence saying why. Versions chain per coffee: v1 → v2 → v3.

**The existing taxonomy stays.** `good | bright | flat | bitter` are already
written to `brews.rating` and already drive the aggregate micron learning in
`recommend.py`. Reusing them avoids a migration and keeps history meaningful.

Lever table — the **single** most telling defect is acted on, the rest are noted:

| Rating | Lever | Change | Why |
|---|---|---|---|
| `bitter` | grind | +30 microns coarser | over-extracting; less surface area |
| `bright` | temp | +2 °C | under-extracting; heat pulls more |
| `flat` | ratio | −0.5 (stronger) | under-dosed for the volume |
| `good` | none | chain ends | stop touching it |

**Key decision — grind is a legal lever here.** The competitor never adjusts
grind automatically, because their product pushes a profile to a machine and
cannot turn your grinder. Coffee Dial has the opposite shape: it *tells you the
setting before you grind*, so grind is the most direct lever available and
should be preferred when the defect is extraction-related. This is a real
architectural advantage of the local, pre-brew model — worth using rather than
copying their constraint.

**Second key decision:** the per-coffee chain **takes precedence** over the
existing aggregate roast-level learning in `recommend.py:70-76`, which stays as
the prior for a coffee you haven't brewed yet. Rejected replacing the aggregate
learning outright — it is the only thing that works on bag one, and it operates
in micron space so it survives a grinder change.

**Contradiction handling:** if a chain has both `bitter` and `bright` recorded
at the same step, they cancel and no change is made, rather than the engine
picking a direction. This is a real case when two people drink from one pot.

**Files:**
- `backend/engine/dialin.py` — created: `next_adjustment(chain, rating)`
- `backend/engine/recommend.py` — modified: accept an optional `chain` and apply
  its accumulated deltas after the base target-micron calc, before clamping
- `backend/app.py` — modified: `brews` gains `parent_brew_id` and `version`;
  new `POST /api/brews/<id>/rate` returning the next recommendation
- `frontend/src/components/RatingRow.jsx` — modified: on rate, show the one
  change and its sentence
- `backend/tests/test_dialin.py` — created

**How it gets proven:**
```bash
backend/venv/bin/python -m pytest backend/tests/test_dialin.py -v
```
Must show: exactly one lever moves per round (assert the other three fields are
byte-identical to the parent); `bitter` then `bitter` again compounds coarser in
the same direction; `bitter` + `bright` together is a no-op; `good` terminates
the chain. Then by hand in the browser: log a brew, rate it bitter, confirm the
next recommendation shows a coarser setting **and** the same temp and ratio.

---

## Step 4 — Aiden profile cleanup

**What:** List profiles on the brewer and delete them by id, so a long dial-in
chain doesn't leave two dozen near-identical profiles on the machine.

**Update:** the listing half is now built, and the `fellow-aiden` dependency
was dropped in the process. That package read profiles from a `profiles` key
inside the device payload, which Fellow's API no longer returns — the stock
library raises `KeyError` on connect, and the workaround for that turned the
schema change into a silent "0 profiles" on an account holding 22. It was also
GPL-3.0 against this project's MIT, and last saw a release in March 2025.

`backend/aiden/client.py` replaces it: ~200 lines, MIT, no monkey-patching, and
it raises on an unexpected payload shape rather than returning an empty list.
`AidenClient.delete_profile()` exists and is unit-tested against stubs, but is
**not** wired to an HTTP route.

**Files:**
- `backend/aiden/client.py` — created: auth, device, profiles, create, delete
- `backend/app.py` — `GET /api/aiden-profiles` built; the `DELETE` route is
  still unbuilt and needs sign-off
- `frontend/src/components/AidenProfile.jsx` — modified: a profile list with
  per-row delete and a confirm step

**Key decision:** delete one profile per call, named explicitly, with a UI
confirm. Rejected a "delete all Coffee Dial profiles" bulk button — an
irreversible action against a physical device you own, driven by a title-prefix
match, is exactly the kind of thing that eats a profile you hand-tuned.

**How it gets proven:** This one cannot be fully verified without your Fellow
credentials in `settings.json`, which are not present. What I can verify is the
endpoint shape against a stubbed client. The live delete has to be run by you,
against one throwaway profile you create first.

---

## Verification plan

**Automatic:**
- `backend/venv/bin/python -m pytest backend/tests/ -v` — freshness and dial-in
  are pure functions and fully unit-testable
- `cd frontend && npm run build` — must stay clean

**By hand, in the browser at localhost:8765:**
- Create a bag with a real roast date, confirm the phase label matches the day count
- Freeze it, confirm the phase stops advancing
- Log a brew, rate it bitter, confirm exactly one number moved

**Cannot be verified here, stated plainly:**
- Anything touching the physical Aiden. No credentials in `settings.json`, and
  no brewer on this network. Profile list and delete are untested against real
  hardware until you run them.
- The freshness constants themselves are *conventions*, not measurements. The
  tests prove the math is internally consistent, not that a light natural is
  genuinely best at day 14. Only your own ratings can tell you that, which is
  what Step 3 is for.

---

## Human sign-off required

- **Step 4, the delete endpoint.** Irreversible data deletion on a device you
  own, authenticated with credentials from `settings.json`. Proposed and held —
  I will not run a live delete against your brewer.
- **Fellow credentials.** They land in `backend/settings.json`, which is
  gitignored (verified). They are stored in plaintext on disk. Acceptable for a
  localhost personal app; worth knowing before you type them.

---

## Assumptions

Scan these — a wrong one is cheap to fix now and expensive later.

1. **Ratings stay four-valued.** Reusing `good/bright/flat/bitter` rather than
   adding `sour/weak/harsh`. If you want a finer defect vocabulary, say so now;
   it changes the lever table and needs a migration.
2. **One bag per coffee at a time.** Rebuying the same coffee resets the clock
   on the existing row rather than creating a second bag.
3. **A brew belongs to at most one bag.** `bag_id` is nullable, so brews logged
   without a bag keep working exactly as today. Nothing existing breaks.
4. **Freshness never blocks a recommendation.** A tired or resting bag shows a
   warning; it does not refuse to generate a recipe.
5. **The deterministic engine stays deterministic.** No AI anywhere in Steps
   1–4. AI stays confined to label parsing and coffee lookup, as it is today.
6. **Storage defaults to `vacuum`,** since that is what you actually use (Fellow
   Atmos). The 1.5 open-clock multiplier behind it is a vendor-derived
   convention, not a measurement — it is the single least-evidenced number in
   this spec, and it is deliberately in the constants block so it is cheap to
   move once your own ratings disagree with it.
7. **Everything runs on localhost, single user, no auth.** The server binds
   `0.0.0.0`, so it is reachable by anything on your home network. That is how
   your phone would reach it, and also means it has no access control.

---

## Deferred

**Bottomless ingest.** No public API exists (searched; nothing documented).
Order emails from `yesreply@bottomless.com` arrive every ~7–10 days and contain
the coffee name, size, and order date — but **no roaster, roast level, roast
date, or tasting notes**. Since Step 1 requires a real roast date, email ingest
cannot feed freshness on its own; it would only pre-fill a coffee name your
existing AI search already handles.

One security note if this is ever revisited: those emails embed a
`app.bottomless.com/magic-link?...&tok=...` URL. That token is a login
credential. It should not be scripted against or stored.

**Phone capture.** The real want. Two pieces are missing, neither large:
1. `POST /api/parse-bag` is text-only — needs an image path to a vision model
2. A camera input in the frontend, which mobile Safari supports natively via
   `<input type="file" accept="image/*" capture="environment">`

The serving side already works: the app is reachable at `http://192.168.0.57:8765`
on your home wifi today. Worth its own spec once these three steps land.
