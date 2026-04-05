# Contributing to Coffee Dial

Thanks for your interest in contributing! The easiest ways to help are adding equipment or recipes — no Python needed.

## Adding a Grinder

Edit `backend/equipment/grinders.json`. Each entry maps grinder settings to micron values. Copy an existing entry as a template. The key fields:

- `name` — display name
- `type` — `electric` or `manual`
- `settings_range` — min/max setting numbers
- `micron_map` — array of `[setting, microns]` pairs (use manufacturer specs or community measurements)

## Adding a Brewer

Edit `backend/equipment/brewers.json`. If your brewer uses an existing recipe type (pour-over, immersion, AeroPress, drip, etc.), it's just a JSON entry. Key fields:

- `extraction_type` — `percolation`, `immersion`, `immersion_fine`, or `immersion_filtered`
- `recipe_type` — which recipe builder to use
- `target_grind_microns` — min/max micron range for this brewer
- `parameters` — temp, ratio, and method-specific settings

## Adding a Community Recipe

Edit `backend/community/recipes.json`. Include:

- `author` and `source_url` — proper attribution is required
- `compatible_brewers` — array of brewer IDs this recipe works with
- `steps` — array of step objects with action, water_g, duration_s, description

## Development Setup

```bash
git clone https://github.com/tshiv/coffee-dial
cd coffee-dial/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp settings.json.example settings.json  # add your API keys
python app.py
```

Open `http://localhost:8765`.

## Pull Requests

- One feature or fix per PR
- Test that the app starts and your changes work end-to-end
- If adding equipment, include your source for micron values in the PR description
- If adding recipes, include attribution and a link to the original source

## Micron Values

Grind particle sizes are approximate. If you have measured data (sieve tests, laser diffraction) for any grinder, that's incredibly valuable — please share it even if you're not sure about the format.

## Questions?

Open an issue. There are no dumb questions.
