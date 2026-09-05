# Backlog

Ideas raised and not built, with enough context to pick up cold. First
written 2026-09-05 at the end of the session that shipped freshness windows,
one-lever dial-in, and the Aiden client; revised the same day after the
session that wired all of it into the frontend.

Ordered by what unblocks the most.

---

## Shipped since the first draft (2026-09-05)

Items 1-3 of the original list are built. What landed, and what changed on
the way:

- **Bag shelf** on the input screen: list, add, open, freeze, thaw, finish,
  rebuy, storage picker, delete. A bag with no roast date shows the
  `awaiting_roast_date` prompt with an inline date field. Selecting a bag
  fills the coffee identity; a search result can be saved as a bag.
- **Freshness line** on the recipe screen, with the same inline prompt.
- **The chain forms.** `/api/recommend` and `POST /api/history` derive a
  child's chain and version from `parent_brew_id` server-side: the parent's
  stored deltas plus the one move its stored rating calls for. The old
  inherit path read the parent's own deltas and dropped its rating, and only
  looked right because the aggregate history bias happened to add the same
  30 microns. A parent rated `bright` would have produced a finer grind
  instead of a hotter brew. The frontend now carries only a parent id.
- **The bag is the chain's anchor.** `GET /api/bags` returns each bag's
  `last_brew`; picking a bag whose last brew was rated offers "continue at
  v(n+1)" or "start fresh". That is how the chain survives a closed tab.
- **Every brew snapshots the bag** (`bag_phase`, `bag_age_days`,
  `bag_open_age_days`, `bag_storage`) at brew time, so item 8 is a single
  query and survives the bag being rebought.
- **Rebuy is a new row**, not a reset of the old one (the spec's assumption 2
  said reset). Brews point at bags by id; resetting the roast date under
  them would have corrupted every earlier snapshot's meaning.
- **Levers respect the brewer.** `recommend.lever_headroom()` reports which
  moves are open; `bright` on a fixed-temperature machine falls back to a
  finer grind, and `bitter` at the brewer's max grind falls back to cooler
  water. Temperature and ratio are now clamped to the brewer's range. Before,
  three `bright` ratings on an Aiden produced 104°C, and a Moccamaster got
  98°C on a machine fixed at 96.
- **Flat from a tired bag moves nothing.** Stale tastes flat; tuning the
  ratio to that would bake a tired bag into the chain.
- **Engine seams moved.** Temperature and ratio are decided once in
  `recommend.compute_targets()` and handed to the recipe builders, which now
  only format. The builders used to recompute ratio themselves, so a chain
  ratio move changed the dose but the recipe still displayed (and history
  stored) the old ratio.
- **History payload fixed.** The recipe screen sent `grind_setting` and
  `temp_f`, which the server silently dropped; history rows had no grind or
  temperature. Now sends the brews-table names plus `process`,
  `target_microns`, `recipe_json`, `bag_id`, `parent_brew_id`, `version`.

Not done from those three items: nothing intentional. Not verified in a
browser: the "save a search result as a bag" prefill path, because the
verification server had no AI key; the form it opens is the same component
the shelf's "add bag" uses, which was exercised.

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

Every number in `engine/freshness.py` is a convention, not a measurement.
The data to check them now accumulates on every brew (`bag_phase`,
`bag_age_days`, `bag_open_age_days`, `bag_storage`, alongside `rating`).

Two things learned while wiring the UI, both worth knowing before touching
the 1.5:

**The `vacuum` multiplier is close to unobservable under the current
constants.** The sealed clock (`TIRED_DAYS`: light 42, medium 30, dark 21)
almost always ends the bag before the open clock does. The open clock can
only be the binding one if the bag was opened before day
`TIRED - open_limit`:

| roast | tired (sealed) | bag_ambient (16.8d) | airtight (21d) | vacuum (31.5d) |
|---|---|---|---|---|
| light | 42 | opened before day 25 | before day 21 | before day 10.5 |
| medium | 30 | before day 13 | before day 9 | never |
| dark | 21 | before day 4 | never | never |

So for a medium or dark roast, `vacuum` and `airtight` produce identical
phases whenever the bag was opened after it finished resting, and no amount
of ratings will separate 1.5 from 1.3 or 2.0. The only thing the ratings can
identify is the *combined* tired day. Calibrate `TIRED_DAYS` first; the
storage multiplier only matters once those are believed.

**The constants contradict the model's own mechanism.** The spec says oxygen
is the dominant staling driver, which is why storage touches only the open
clock. But a sealed one-way-valve bag has almost no oxygen in it and still
tires at 30 days on the sealed clock. If oxygen dominates, the sealed tired
day should be much longer and the open clock should bind most of the time;
if sealed bags really do tire at 30 days, something other than oxygen is
doing it (volatile loss through the valve, lipid oxidation from residual
O2), and a vacuum bonus of 50% is too generous. Pick one.

What a better number would rest on:
- For `TIRED_DAYS`: your own ratings vs `bag_age_days`, once there are ~30
  rated brews per roast level. That is the identifiable quantity.
- For the storage multiplier: a split-bag test. One bag, two halves, Atmos vs
  a plain canister, both opened the same day, one cup from each per day,
  rated blind. Three weeks. Nothing else will tell you.
- For `READY_RANGE_DAYS`: the degassing literature gives the *shape* (darker
  roasts degas faster; Smrke et al. 2017/2018 measured whole-bean CO2 loss
  gravimetrically) but the "ready" threshold is a taste call, which the
  ratings are for.

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
