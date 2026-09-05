# Backlog

Ideas raised and not built, with enough context to pick up cold. Written
2026-09-05, at the end of the session that shipped freshness windows, one-lever
dial-in, and the Aiden client.

Ordered by what unblocks the most.

---

## 1. Freshness has no UI at all

**The biggest gap in the current state.** Steps 1 and 2 of
[the spec](spec-freshness-and-dialin.md) shipped as backend only. `GET/POST/PUT/DELETE
/api/bags` all work and are tested, `engine/freshness.py` is fully unit-tested,
and **nothing in the frontend calls any of it.**

Needed:
- A bag shelf: list bags with phase (`resting` / `ready` / `tired`), the ready
  range, and days off roast
- Create a bag, with a **required** roast date — a bag without one must show the
  `awaiting_roast_date` prompt, never a fabricated window
- Actions: open, freeze, thaw, finish, rebuy. All are already server-side
- Storage picker (`bag_ambient` / `airtight` / `vacuum`), defaulting to `vacuum`
- A freshness line on the recipe screen for the bag being brewed

Model the screen on `views/AidenProfilesView.jsx`, which is the newest pattern
in the codebase.

## 2. The dial-in chain does not persist across brews

`RatingRow` shows the next change correctly (verified). But logging the *next*
brew does not set `parent_brew_id`, so the v1 → v2 → v3 chain never actually
forms — every brew starts from the base recommendation again.

The backend is ready: `POST /api/history` accepts `parent_brew_id`, `version`,
and the three `chain_*` columns, and `POST /api/recommend` accepts either an
explicit `chain` or a `parent_brew_id` to inherit from.

What's missing is frontend state: carry the rated brew's id and chain into the
next recommendation request, and show which version you're on.

## 3. Bags are not linked to brews

`brews.bag_id` exists and is nullable. Nothing sets it. Until it does, freshness
and brew history are two unrelated datasets, and questions like "did the cups I
rated bitter come from bags past their window?" can't be asked.

## 4. Phone capture — the actual want

Stated goal: photograph a bag or a Bottomless order email from a phone.

Two pieces missing:
1. `POST /api/parse-bag` is text-only. Needs an image path to a vision model.
   `ai/parsing.py` already has the provider plumbing.
2. A camera input in the frontend. Mobile Safari supports it natively:
   `<input type="file" accept="image/*" capture="environment">`

The serving side already works — the Flask app binds `0.0.0.0` and is reachable
on the LAN at `http://192.168.0.57:8765`. **No auth of any kind**, so anything
on the home network can reach it. Worth deciding whether that matters before
leaning on it.

## 5. Aiden dashboard

Taylor's idea, explicitly deferred to its own session. The listing view proved
what data exists to build on:

- 22 profiles, grouped by Fellow's folder
- Device totals: `totalBrewingCycles` (948), `totalWaterVolumeL`
- Live device state in the payload: `brewing`, `brewingProfileId`, `heaterOn`,
  `lidClosed`, `missingWater`, `carafePresent`, `isConnected`, `firmwareVersion`
- Schedules exist on the API (`/devices/{id}/schedules`) and are **not** yet
  exposed by `AidenClient`

Hard constraint discovered: **there is no per-profile brew counter.** Any
"most brewed" panel would have to be built from Coffee Dial's own history, not
from Fellow.

## 6. Per-pulse temperature ramps

`engine/recipes.py` emits one flat temperature for every pulse. Real profiles on
the brewer don't: the Onyx Yabitu Koba profile ramps **205 → 200 → 190°F**
across three pulses, and several Fellow drops do the same.

`ssPulseTemperatures` is a per-pulse array, so the capability is there and the
engine simply isn't using it. Whether a descending ramp is actually better is an
open question — that's what the dial-in loop is for.

## 7. The grinder catalog is the weakest point

11 grinders. The nearest competitor lists 200+. For personal use exactly one
matters, so this is low priority — but it is the first thing anyone else
notices, and `equipment/grinders.json` is just data.

## 8. Calibrate the freshness constants

Every number in `engine/freshness.py` is a convention, not a measurement. The
weakest is the `vacuum` open-clock multiplier (1.5×), which derives from a
vendor marketing claim rather than any independent test.

Once there are enough rated brews with bag ages attached (needs item 3), these
can be checked against reality instead of taken on faith.

## 9. Operational: the database location

`COFFEE_DIAL_DB` defaults to `backend/coffee_dial.db`, relative to the checkout.
Work done in a git worktree writes to that worktree's copy and is lost when it
is removed. For daily use, run from the main checkout and point
`COFFEE_DIAL_DB` somewhere permanent.

---

## Decided against

**Deleting Aiden profiles.** `AidenClient.delete_profile()` is implemented and
unit-tested, including that a bad id raises without issuing an HTTP DELETE. It
is deliberately **not** routed, and Taylor has said he does not want deletion.
Leave it unrouted unless that changes.

## Deferred with reasons

**Bottomless ingest.** No public API exists. Order emails from
`yesreply@bottomless.com` arrive every ~7–10 days and contain the coffee name,
size, and order date — but no roaster, roast level, roast date, or tasting
notes. Since freshness requires a real roast date, email ingest cannot feed it;
it would only pre-fill a name the existing AI search already handles. Superseded
by item 4.

Security note if it is ever revisited: those emails embed an
`app.bottomless.com/magic-link?...&tok=...` URL. That token is a login
credential and must not be scripted against or stored.

**Filing the upstream `fellow-aiden` bug.** The package reads profiles from a
key Fellow no longer returns. It was dropped from this project rather than
patched. Reporting it upstream would help others, but the repo's last release
was March 2025 and a "push to pip" request has sat open since August 2025, so
expect no response.
