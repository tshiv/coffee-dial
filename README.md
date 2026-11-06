# Coffee Dial

**Open source bag-to-cup brew assistant.** AI-powered grind settings and brew recipes for 11 grinders and 21 brewers, plus 13 curated community recipes from coffee experts.

Built for coffee snobs on rotating subscriptions (e.g. [Bottomless](https://www.bottomless.com)) who want dialed-in settings for every new bag without guesswork.

---

## What it does

1. **Search or paste** your coffee bag info — coffee name, bag text, Bottomless description, anything
2. **AI parses** roast level, origin, processing method, and flavor notes (Anthropic or OpenAI)
3. **Shelve the bag** with its roast date — the app tracks when it's still resting, ready, or past its best
4. **Pick your equipment** — grinder + brewer from the catalog
5. **Tell it how much** — just ounces, the engine computes dose and ratio
6. **Get a complete recipe** — grind setting for your specific grinder + method-specific brew instructions
7. **Browse community recipes** — matching recipes from Hoffmann, Rao, Kasuya, and others, plus the roaster's own published recipe when it can find one
8. **Rate the cup** — good, bright, flat, or bitter — and the next recipe for that bag changes one thing to fix it

---

## Supported Equipment

### Grinders

| Grinder | Type | Settings |
|---------|------|----------|
| Fellow Ode Gen 1 | Electric | 1–11 |
| Fellow Ode Gen 2 | Electric | 1–31 |
| Fellow Opus | Electric | 1–41 |
| Baratza Encore | Electric | 1–40 |
| Baratza Encore ESP | Electric | 1–40 |
| Baratza Virtuoso+ | Electric | 1–40 |
| Comandante C40 | Manual | Clicks |
| 1Zpresso JX-Pro | Manual | Clicks |
| 1Zpresso J-Max | Manual | Clicks |
| Timemore C2 | Manual | Clicks |
| Timemore C3 | Manual | Clicks |

### Brewers

**Automatic:** Fellow Aiden, Breville Precision Brewer, Technivorm Moccamaster (KBGV, KBT), Ratio Six, Ratio Eight, OXO Brew 9-Cup, Bonavita Connoisseur

**Manual:** Hario V60 (01/02/03), Chemex (3/6/8-cup), Kalita Wave (155/185), Fellow Stagg [X]/[XF], AeroPress, Clever Dripper, French Press

---

## How it works

### The Micron Bridge

Every grinder produces a particle size in microns. Every brewer has an ideal micron range. The recommendation engine:

1. Determines a **target micron value** based on roast level + extraction type (percolation, immersion, immersion-fine for AeroPress, immersion-filtered for Clever Dripper)
2. Applies **offsets** for origin, process, batch size, and your brew history
3. **Translates** the target to your grinder's specific setting via interpolation
4. **Generates a recipe** appropriate for your brewer (step-by-step pour-over, steep time, Aiden profile, etc.)

### Dialing in, one change at a time

Each rating moves exactly one variable, and the recipe says which one and why:

| Rating | Means | First move | If that's blocked |
|---|---|---|---|
| Bitter | Over-extracted | One grind setting coarser | A little cooler |
| Bright / sour | Under-extracted | A little hotter | One grind setting finer |
| Flat | Weak | Stronger ratio | — |
| Good | Dialed in | Nothing changes | — |

A grind move always lands on a different number on your dial, even on coarse-stepped grinders like the Ode Gen 1. "Blocked" means the brewer can't make that move: a fixed-temperature machine has no temperature lever, and an Aiden already at 99°C can't go hotter. Changes build on each other cup by cup, so the third cup of a coffee starts from where the second left off. If you ground at a different setting than the one recommended, log it and the next recipe starts from what you actually used.

### Freshness

Each bag on the shelf runs two clocks, and whichever runs out first wins:

- **Since roast:** light roasts rest about 10–20 days, medium 5–12, dark 2–5 (natural and anaerobic coffees get 3 extra days). A sealed bag goes tired around day 42 (light), 30 (medium), or 21 (dark); decaf sooner.
- **Since opening:** about three weeks, longer in a vacuum canister and shorter in the bag it came in.

Freezing pauses both clocks. Freshness also shapes the dial-in: a cup rated while the bag is still resting is flagged as a moving target, and "flat" from a tired bag changes nothing, since that's what stale coffee tastes like.

### Learning from your history

A new coffee with no ratings yet starts from your history with that roast level. If most of your last 20 rated cups of light roasts came out bitter, the next light roast starts a notch coarser; mostly bright, a notch finer. Good cups count against moving, and cups from tired bags are ignored. Adjustments happen in microns, so they carry over if you switch grinders.

### Micron values are approximate

Grind particle sizes are based on manufacturer specs and community measurements. They vary by burr wear, alignment, and bean hardness. **Please contribute corrections** — this is the primary area where community input will improve the tool.

---

## Setup

### 1. Clone

```bash
git clone https://github.com/tshiv/coffee-dial
cd coffee-dial
```

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

> **macOS note:** A virtual environment is required on modern macOS due to [PEP 668](https://peps.python.org/pep-0668/) (externally-managed Python). The commands above handle this.

The API server runs at `http://localhost:8765`.

By default it only listens on this computer. Coffee Dial has no login, so
anything that can reach the port can read your history and use your saved API
key. Two opt-in environment variables:

| Variable | Effect |
|---|---|
| `COFFEE_DIAL_HOST=0.0.0.0` | Listen on your home network too (e.g. to use it from your phone). Only do this on a network you trust. |
| `COFFEE_DIAL_ALLOWED_HOSTS=my-mac.local` | Extra hostnames to accept, comma-separated. Localhost and IP addresses always work; any other name is refused, which blocks DNS-rebinding attacks from web pages. |
| `COFFEE_DIAL_DEBUG=1` | Flask debug mode with auto-reload. Its in-browser debugger can run code on your machine, so keep it local. |

### 3. Frontend

```bash
cd frontend
npm install
npm run build
```

For production, Flask serves the built frontend from `frontend/dist/` — navigate to `http://localhost:8765`.

For development, run the Vite dev server alongside the backend:

```bash
cd frontend
npm run dev
```

Vite starts at `http://localhost:5173` and proxies `/api` requests to the backend on port 8765.

### 4. Add your API key

In the app → Settings → paste your Anthropic or OpenAI key.

---

## Configuration

All settings are stored in `backend/settings.json` (gitignored):

```json
{
  "ai_provider": "anthropic",
  "anthropic_key": "sk-ant-...",
  "temp_unit": "F",
  "default_roast": "medium-light",
  "fellow_email": "you@email.com",
  "fellow_password": "..."
}
```

Temperature displays in Fahrenheit by default (changeable in Settings).

`default_roast` is the roast the engine assumes when a bag's own roast can't be read
(`light`, `medium-light`, `medium`, `medium-dark`, `dark`; defaults to `medium`). Set it
to match your subscription profile so an unparsed bag gets the right grind, ratio, and
rest window instead of a medium-roast guess.

---

## Community Recipes

Coffee Dial shows curated community recipes from well-known coffee experts alongside the engine's personalized recommendation. After generating a recommendation, you'll see matching recipes you can use instead — or combine with the engine's grind setting.

### 13 curated recipes

Hoffmann V60/French Press/AeroPress, Kasuya 4:6, Rao V60, Adler AeroPress, Chemex Classic, Kalita Wave, Clever Dripper, Stagg Pour-Over, Aiden Light/Dark Roast defaults, and Moccamaster best practices.

### AI roaster search

For a bag with a roaster, Coffee Dial searches the web (Claude with web search) for that roaster's own published recipe for your brewer. Results link to the source page (flagged if the search never actually opened it), show a confidence badge (high/medium/low) with the reason, and are scaled to your brew size. Each lookup is cached for 30 days. Searches take up to a minute or two and need an Anthropic key; with only an OpenAI key, the lookup falls back to what the model remembers.

### Brew.link import (Aiden)

Paste a Fellow brew.link URL to import shared Aiden profiles directly. The imported profile can be pushed straight to your Aiden.

### Attribution

All community recipes credit their original authors and link to source material.

---

## Fellow Aiden Integration

For Fellow Aiden owners: the app can push brew profiles directly to your Aiden through Fellow's account API. Add your Fellow credentials in Settings.

- **Engine profiles** — push the engine's recommendation directly
- **Community profiles** — load a curated Aiden recipe (light/dark roast defaults) into the profile, then push it
- **Brew.link imports** — import a shared profile from Fellow's sharing URLs, then push it
- **Profiles on your brewer** — browse the profiles already saved on your Aiden

This uses Fellow's private, undocumented account API, not a public one. It can change or break without notice.

---

## Project Structure

```
coffee-dial/
  backend/
    app.py                  # Flask API + static serving from frontend/dist
    ai/
      parsing.py            # AI provider integration
      recipe_search.py      # AI-powered roaster recipe search
    aiden/
      client.py             # Minimal Fellow Aiden account API client
    engine/
      recommend.py          # Recommendation pipeline
      grind.py              # Micron targeting + grinder translation
      dialin.py             # One-change-per-rating dial-in chain
      freshness.py          # Resting / ready / tired phases per bag
      recipes.py            # Recipe builders per brew method
    equipment/
      grinders.json         # Grinder catalog (add yours here!)
      brewers.json          # Brewer catalog
      loader.py             # Equipment loading
    community/
      recipes.json          # Curated community recipes (add yours!)
      loader.py             # Recipe search + scaling
      brewlink.py           # Fellow brew.link import
    tests/                  # pytest suite (pip install -r requirements-dev.txt)
  frontend/
    package.json            # Preact + Vite
    vite.config.js          # Dev server + API proxy
    index.html              # Vite entry point
    src/
      main.jsx              # App entry
      app.jsx               # Root component + view routing
      theme/                # CSS custom properties, light/dark modes
      hooks/                # useApi, useBags, useEquipment, useTheme, useTimer
      lib/                  # Format and freshness helpers
      components/           # Header, CoffeeSearch, CoffeeIdentity, BagForm,
                            # BagShelf, FreshnessLine, SizePicker, RecipeCard,
                            # AidenProfile, PourOverSteps, BrewTimer,
                            # SimpleDrip, RatingRow
      views/                # SetupView, InputView, RecipeView, SettingsView,
                            # HistoryView, AidenProfilesView
  docs/                     # Design spec and backlog
```

## Contributing

The easiest ways to contribute:

- **`backend/equipment/grinders.json`** — Add a grinder or correct micron maps
- **`backend/equipment/brewers.json`** — Add a brewer or adjust grind ranges
- **`backend/community/recipes.json`** — Add a community brew recipe with attribution

Adding a new grinder is just a JSON entry — no Python code changes needed. Adding a new brewer that uses an existing recipe type (pour-over, immersion, etc.) is also just JSON. Adding a community recipe is also just a JSON entry with author and source URL.

---

## Stack

- **Frontend**: Preact + Vite + CSS Modules — component architecture with warm parchment design system, light/dark mode, brew timer
- **Backend**: Python 3 + Flask + SQLite
- **AI**: Anthropic Claude Haiku 5.5 for bag parsing (structured outputs), Claude Opus 5.5 with web search for roaster recipes; OpenAI GPT-4o-mini as an alternative for parsing and recall-only recipe lookups
- **Aiden API**: a minimal in-repo client (`backend/aiden/client.py`), originally based on [9b/fellow-aiden](https://github.com/9b/fellow-aiden)

---

## Related projects & inspirations

- [9b/fellow-aiden](https://github.com/9b/fellow-aiden) — Python library + Brew Studio for Fellow Aiden
- [Timer.Coffee](https://github.com/antonkarliner/timer-coffee) — open source brew timer with community recipes (inspiration for the community recipes feature)
- [Beanconqueror](https://github.com/graphefruit/Beanconqueror) — open source coffee tracking mobile app (excellent data model reference)
- [brewshare.coffee](https://brewshare.coffee) — community Aiden profile browser

---

## License

MIT
