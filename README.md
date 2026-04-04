# Coffee Dial

**Open source bag-to-cup brew assistant.** AI-powered grind settings and brew recipes for 11 grinders and 21 brewers.

Built for coffee snobs on rotating subscriptions (e.g. [Bottomless](https://www.bottomless.com)) who want dialed-in settings for every new bag without guesswork.

---

## What it does

1. **Search or paste** your coffee bag info — coffee name, bag text, Bottomless description, anything
2. **AI parses** roast level, origin, processing method, and flavor notes (Anthropic or OpenAI)
3. **Pick your equipment** — grinder + brewer from the catalog
4. **Tell it how much** — just ounces, the engine computes dose and ratio
5. **Get a complete recipe** — grind setting for your specific grinder + method-specific brew instructions
6. **Rate the cup** → app adjusts future recommendations based on your history

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

1. Determines a **target micron value** based on roast level + brew method (percolation vs immersion)
2. Applies **offsets** for origin, process, batch size, and your brew history
3. **Translates** the target to your grinder's specific setting via interpolation
4. **Generates a recipe** appropriate for your brewer (step-by-step pour-over, steep time, Aiden profile, etc.)

### Brew history learning

After rating a few cups, the app adapts. If you consistently rate light Ethiopian coffees as too bitter, it nudges the grind coarser for your next one. Learning happens in micron-space, so feedback transfers even if you switch grinders.

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
pip install -r requirements.txt
python app.py
```

The backend runs at `http://localhost:8765`.

### 3. Open the app

Navigate to `http://localhost:8765` — Flask serves both the backend API and the frontend.

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
  "fellow_email": "you@email.com",
  "fellow_password": "..."
}
```

Temperature displays in Fahrenheit by default (changeable in Settings).

---

## Community Recipes

Coffee Dial includes curated community recipes from well-known coffee experts alongside the engine's personalized recommendation. After generating a recommendation, you'll see matching community recipes you can use instead.

### Sources

- **Curated recipes** — Hoffmann V60, Kasuya 4:6, Rao V60, and more, stored in `backend/community/recipes.json`
- **AI roaster search** — Ask AI for a specific roaster's brew guide (e.g., "Counter Culture Hologram on V60")
- **Brew.link import** — Paste a Fellow brew.link URL to import shared Aiden profiles

### Attribution

Community recipes credit their original authors and link to source material. AI-searched recipes show a confidence badge indicating how certain the AI is about the recommendation.

---

## Aiden Push

For Fellow Aiden owners: the app can push brew profiles directly to your Aiden via the [9b/fellow-aiden](https://github.com/9b/fellow-aiden) library. Add your Fellow credentials in Settings. Community recipes with Aiden profiles can also be pushed directly.

---

## Project Structure

```
coffee-dial/
  backend/
    app.py                  # Flask routes + frontend serving
    ai/
      parsing.py            # AI provider integration
      recipe_search.py      # AI-powered roaster recipe search
    engine/
      recommend.py          # Recommendation pipeline
      grind.py              # Micron targeting + grinder translation
      recipes.py            # Recipe builders per brew method
      adjustments.py        # Origin/process/volume offsets
    equipment/
      grinders.json         # Grinder catalog (add yours here!)
      brewers.json          # Brewer catalog
      loader.py             # Equipment loading
    community/
      recipes.json          # Curated community recipes (add yours!)
      loader.py             # Recipe search + scaling
      brewlink.py           # Fellow brew.link import
  frontend/
    index.html              # Single-file frontend (no build step)
```

## Contributing

The easiest ways to contribute:

- **`backend/equipment/grinders.json`** — Add a grinder or correct micron maps
- **`backend/equipment/brewers.json`** — Add a brewer or adjust grind ranges
- **`backend/community/recipes.json`** — Add a community brew recipe with attribution

Adding a new grinder is just a JSON entry — no Python code changes needed. Adding a new brewer that uses an existing recipe type (pour-over, immersion, etc.) is also just JSON. Adding a community recipe is also just a JSON entry with author and source URL.

---

## Stack

- **Frontend**: Vanilla HTML/CSS/JS, no framework, no build step
- **Backend**: Python + Flask + SQLite
- **AI**: Anthropic Claude Haiku or OpenAI GPT-4o-mini
- **Aiden API**: [9b/fellow-aiden](https://github.com/9b/fellow-aiden)

---

## Related projects & inspirations

- [9b/fellow-aiden](https://github.com/9b/fellow-aiden) — Python library + Brew Studio for Fellow Aiden
- [Timer.Coffee](https://github.com/antonkarliner/timer-coffee) — open source brew timer with community recipes (inspiration for the community recipes feature)
- [Beanconqueror](https://github.com/graphefruit/Beanconqueror) — open source coffee tracking mobile app (excellent data model reference)
- [brewshare.coffee](https://brewshare.coffee) — community Aiden profile browser

---

## License

MIT
