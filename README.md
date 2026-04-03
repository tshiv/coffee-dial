# ☕ Coffee Dial

**AI-powered grind settings and brew profiles for the Fellow Ode Gen 1 + Aiden.**

Built for households on a rotating coffee subscription (e.g. [Bottomless](https://www.bottomless.com)) who want dialed-in settings for every new bag without guesswork.

![Coffee Dial Screenshot](docs/screenshot.png)

---

## What it does

1. **Search or paste** your coffee bag info — coffee name, bag text, Bottomless description, anything
2. **AI parses** roast level, origin, processing method, and flavor notes (OpenAI or Anthropic)
3. **Recommends** a specific Ode Gen 1 grind setting (1–11) and a full Aiden brew profile
4. **Optionally pushes** the profile directly to your Aiden via the Fellow API
5. **You rate the cup** → app adjusts future recommendations based on your history

---

## Setup

### 1. Clone

```bash
git clone https://github.com/coffee-dial/coffee-dial
cd coffee-dial
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The backend runs at `http://localhost:8765`. It handles:
- AI coffee parsing (Anthropic or OpenAI)
- SQLite brew history persistence
- Fellow Aiden profile push via [9b/fellow-aiden](https://github.com/9b/fellow-aiden)

### 3. Frontend

Open `frontend/index.html` in your browser. That's it — no build step.

Or serve it:

```bash
cd frontend
python -m http.server 3000
# → http://localhost:3000
```

### 4. Add your API key

In the app → Settings → paste your Anthropic or OpenAI key.

---

## Configuration

All settings are stored in `backend/settings.json` (gitignored):

```json
{
  "ai_provider": "anthropic",
  "anthropic_key": "sk-ant-...",
  "openai_key": "sk-...",
  "fellow_email": "you@email.com",
  "fellow_password": "..."
}
```

The database lives at `backend/coffee_dial.db` (also gitignored).

---

## How recommendations work

### Ode Gen 1 grind settings (batch brew)

| Roast        | Base setting | Temp   |
|-------------|-------------|--------|
| Light        | 4           | 96°C   |
| Medium-Light | 5           | 94°C   |
| Medium       | 6           | 93°C   |
| Medium-Dark  | 7           | 91°C   |
| Dark         | 8           | 89°C   |

Adjustments applied on top of the base:

- **Origin** — Ethiopian/Kenyan +1°C; Brazilian/Sumatran +0.5 grind, -2°C
- **Process** — Washed +1°C; Natural/Honey +0.5 grind, -1°C; Anaerobic +1 grind, -1°C
- **Batch size** — >22oz +0.5 grind, ≤10oz -0.5 grind
- **Your history** — if 2+ similar brews rated bitter → +0.5 grind; bright/flat → -0.5 grind

### Brew history learning

After rating a few cups, the app adapts. If you consistently rate light Ethiopian coffees as too bitter, it'll nudge the grind setting coarser for your next one. The adjustment is averaged across similar brews (same roast level).

---

## Aiden push

Uses the unofficial [9b/fellow-aiden](https://github.com/9b/fellow-aiden) Python library. The backend authenticates with your Fellow account and creates a profile with:

- Temperature
- Bloom duration + ratio
- Pulse count + interval
- Brew ratio

Profiles appear in your Fellow app immediately.

---

## Brew presets

Default presets (editable in Settings):

| Name         | Volume  | Dose  |
|-------------|---------|-------|
| Solo (12.5oz)| 12.5 oz | 22g   |
| Partner (14oz)| 14 oz   | 24.5g |
| Batch (30oz) | 30 oz   | 52g   |

---

## Stack

- **Frontend**: Vanilla HTML/CSS/JS, no framework, no build step
- **Backend**: Python + Flask + SQLite
- **AI**: Anthropic Claude Haiku or OpenAI GPT-4o-mini
- **Aiden API**: [9b/fellow-aiden](https://github.com/9b/fellow-aiden)

---

## Related projects

- [9b/fellow-aiden](https://github.com/9b/fellow-aiden) — Python library + Brew Studio (Streamlit UI with AI)
- [Beanconqueror](https://github.com/graphefruit/Beanconqueror) — open source coffee tracking mobile app
- [brewshare.coffee](https://brewshare.coffee) — community Aiden profile browser

---

## License

MIT
