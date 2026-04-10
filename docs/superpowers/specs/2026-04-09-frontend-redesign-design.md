# Coffee Dial Frontend Redesign

**Date:** 2026-04-09
**Status:** Approved
**Author:** Taylor + Claude

## Problem

Coffee Dial's frontend is a 1,220-line monolithic HTML file with inline CSS and JavaScript. No framework, no build tools, no component structure. The UI was built fast and it shows: dark-only theme, 480px max-width that looks cramped on desktop, developer-tool aesthetic, and a three-screen wizard flow that adds friction to a once-a-week task.

The app works. The backend is solid. The frontend needs to match.

## Goals

1. Rebuild the frontend on a maintainable, component-based architecture
2. Ship a visual design that feels intentional -- warm, typographic, confident
3. Support light and dark mode with warm palettes in both
4. Reduce the user flow from three screens to two
5. Make the coffee the hero, not the grind number
6. Add a brew timer for manual methods (pour-over, AeroPress)
7. Make the app look good on both phone and desktop without a separate layout

## Non-Goals

- Changing the backend (Flask API stays as-is)
- Adding new API endpoints
- PWA/offline support (future consideration)
- User accounts or cloud sync

## Stack

### Vite + Preact + CSS Modules

**Vite** for the build step. Zero-config, sub-second hot reload, outputs static files that Flask serves. No webpack, no config files to maintain.

**Preact** for components. Same API as React (JSX, hooks) but 3kb. The most well-represented framework in LLM training data, which matters because Claude will be writing most of this code. Any React developer can contribute without learning a niche framework.

**CSS Modules** for scoped styles. Each component gets its own `.module.css` file. The existing CSS custom properties (design tokens) carry over as a shared theme file.

### Build Output

Vite builds to `frontend/dist/`. Flask serves this directory as static files. The development workflow is:

- `cd frontend && npm run dev` for hot-reload dev server (proxies API to Flask)
- `cd frontend && npm run build` to produce static assets
- Flask serves `frontend/dist/index.html` and static assets in production

### File Structure

```
frontend/
  src/
    main.jsx                  # Entry point
    app.jsx                   # Root component, view router
    theme/
      tokens.css              # CSS custom properties (colors, spacing, radii)
      light.css               # Light mode token overrides
      dark.css                # Dark mode token overrides
      global.css              # Reset, base typography, shared utilities
    components/
      Header.jsx              # Logo + title + equipment context + gear icon
      Header.module.css
      CoffeeSearch.jsx        # Search input + paste toggle + AI status
      CoffeeSearch.module.css
      CoffeeIdentity.jsx      # Coffee name, roaster, origin, tags, notes
      CoffeeIdentity.module.css
      SizePicker.jsx           # Preset cards + custom oz input
      SizePicker.module.css
      RecipeCard.jsx           # Key-value recipe list (grind, temp, dose, water, ratio)
      RecipeCard.module.css
      AidenProfile.jsx         # Aiden-specific profile grid + push button
      AidenProfile.module.css
      PourOverSteps.jsx        # Timed step list with vertical timeline
      PourOverSteps.module.css
      BrewTimer.jsx            # Start/reset timer with step-aware highlighting
      BrewTimer.module.css
      SimpleDrip.jsx           # Single paragraph brew instructions
      SimpleDrip.module.css
      RatingRow.jsx            # Post-brew rating buttons + save
      RatingRow.module.css
    views/
      SetupView.jsx            # First-run grinder + brewer selection
      InputView.jsx            # Screen 1: search + coffee identity + size picker
      RecipeView.jsx           # Screen 2: full recipe card, brewer-adaptive
      SettingsView.jsx         # Gear icon destination
      HistoryView.jsx          # Brew log
    hooks/
      useApi.js                # Fetch wrapper with server status
      useTheme.js              # Light/dark mode toggle, persisted to localStorage
      useEquipment.js          # Grinder/brewer state, persisted to localStorage
      useTimer.js              # Brew timer logic (start, pause, reset, step transitions)
    lib/
      format.js                # Temperature conversion, display helpers
  index.html                   # Vite entry HTML
  vite.config.js               # Proxy /api to Flask backend
  package.json
```

## Visual Design

### Palette

Warm parchment tones. The warmth comes from the background, not from accent colors splashed everywhere.

**Light mode:**
- Background: `#FAF7F2` (parchment)
- Surface: `#F3EDE4` (linen)
- Border: `#E4D9CB`
- Text primary: `#2C1E12` (espresso)
- Text secondary: `#6B5744` (roasted)
- Text muted: `#9B8B7A` (kraft)
- Accent (interactive only): `#C8854A` (amber)
- CTA background: `#3C2A1A` (dark roast)
- CTA text: `#F3EDE4`

**Dark mode:**
- Background: `#1A1714` (dark roast)
- Surface: `#241F1A` (dark linen)
- Border: `#2E271F`
- Text primary: `#F0E6D8` (cream)
- Text secondary: `#A89880`
- Text muted: `#7A6B5A`
- Accent: `#C8854A` (same amber)
- CTA background: `#C8854A`
- CTA text: `#1A1714`

Dark mode is the same room with the lights dimmed. Same warmth, same palette family, just inverted value scale.

### Typography

System font stack: `-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif`.

- Coffee name (page title): 24px, weight 800, tight letter-spacing (-0.5px)
- Section labels: 11px, weight 600, uppercase, letter-spacing 1.5px, muted color
- Recipe values: 17-18px, weight 700
- Recipe labels: 13px, normal weight, muted color
- Body text: 14px
- Small labels/tags: 10-11px

Typography is the primary design element. Hierarchy comes from size and weight, not color or decoration.

### Layout

Centered column, max-width ~520px. Content never stretches. On mobile, the column fills the viewport with padding. On desktop, it sits centered with the background visible on both sides.

No cards with borders around everything. Content is separated by whitespace and thin rules (`1px solid border-color`). The coffee identity block and Aiden profile grid get a surface-color background to group related information, but most content sits directly on the page background.

### Logo

Abstract dial mark -- a circle with a notch inside a rounded square. Not a coffee cup emoji. Says "precision tool" not "coffee shop."

## User Flow

### First Run: Setup

If `localStorage` has no `cd_setup_complete` flag, show the setup view:

- Centered logo + "Coffee Dial" title
- Grinder dropdown (populated from `/api/equipment`)
- Brewer dropdown
- "Let's Brew" button

Saves selections to localStorage, sets the flag, navigates to the input view. Never shown again.

### Screen 1: Input View

The daily landing screen. Everything needed to describe the brew.

**Header:** Logo + "Coffee Dial" + equipment context text (e.g., "Ode G1 . Aiden") + gear icon button.

**Coffee search section:**
- Toggle between "Search" and "Paste bag info"
- Search input with submit button
- AI status indicator (spinner + text) while searching
- On result: coffee identity block appears below with name (large), roaster + city, roast level tag, origin/process tags, tasting notes in italics

**Size picker section:**
- Always visible (size selection doesn't depend on coffee detection)
- Named preset cards (Solo 12oz, Two Cups 20oz, Batch 32oz) as tappable buttons
- Custom oz input row
- Selected state is visually distinct (dark background, light text)

**CTA button:** "Get my recipe" -- navigates to screen 2. Disabled until coffee is detected and size is selected.

### Screen 2: Recipe View

The output screen. A reference card for this specific brew.

**Back link:** "Change coffee" returns to screen 1 with state preserved.

**Coffee as page title:**
- Coffee name at 24px bold (e.g., "Hologram")
- Roaster + origin + roast level below
- Tasting notes in italics
- Context line: "Brewing 12oz on Ode Gen 1 > Aiden"

**Recipe parameters** as a key-value list:
```
Grind setting          4
Water temperature      205 F
Coffee                 21.5g
Water                  344g
Ratio                  1:16
```

No grid, no boxes around each number. Left-aligned labels in muted color, right-aligned values in bold. Separated by thin rules.

**Brewer-specific section** (appears below the recipe list):

- **Fellow Aiden:** Profile grid (bloom time, bloom ratio, pulses, pulse interval, temperature, ratio) in a 3-column grid with surface background. "Push to Aiden" CTA button below. Profile name input for the push.

- **Pour-over (V60, Chemex, Kalita, Stagg X):** Timed step list with vertical timeline rail. Each step shows: step name (e.g., "Bloom"), instruction with gram target in bold (e.g., "Pour to 45g, stir gently"), time range (e.g., "0:00-0:45"). Dot on the timeline for each step. Below the steps: brew timer component.

- **AeroPress / Clever Dripper:** Same timed step format as pour-over, adapted for immersion. Includes steep time. Timer below.

- **Simple drip (Moccamaster, Ratio Six, OXO):** Single paragraph of plain-language instructions. No timer, no steps, no profile grid. Just grind and go.

**Brew timer** (manual methods only):
- Large tabular-nums display (36px)
- Start / Reset buttons
- Current step highlights automatically as time progresses
- Optional: gentle alert (vibration on mobile) at step transitions
- Timer is absent entirely for Aiden and simple drip brewers

**Learning note:** When brew history adjusts a recommendation, a small note appears below the recipe list explaining why (e.g., "Adjusted coarser -- 2 recent bitter brews with similar light roasts"). Yellow/amber tint, not prominent but visible.

**Rating row:** After brewing, four buttons (Too Bitter, Too Bright, Flat/Weak, Just Right) + Save to History. Same as current functionality.

**"Brew something else"** button at the bottom returns to screen 1 with state cleared.

### Settings View

Accessed via gear icon in the header. "Done" button returns to the previous screen.

Contains:
- Equipment (grinder + brewer dropdowns)
- Volume presets (list with add/delete)
- AI provider (Anthropic/OpenAI) + API key
- Temperature unit (F/C)
- Theme toggle (light/dark/system)
- Fellow credentials (email + password for Aiden push)
- Brew history count + "View" button + "Clear all" button
- Backend server status
- About section

### History View

Accessed from Settings > Brew History > View. "Done" returns to settings.

Chronological list of saved brews. Each entry shows: date, coffee name, roast/origin metadata, grind setting, volume, dose, rating badge. Same data as current implementation.

## Theme System

CSS custom properties defined in `tokens.css`. Light and dark overrides in separate files. Theme preference stored in localStorage (`cd_theme`: `light`, `dark`, or `system`).

When set to `system`, respect `prefers-color-scheme` media query. Apply the appropriate class to the document root (`data-theme="light"` or `data-theme="dark"`).

Components use `var(--color-bg)`, `var(--color-surface)`, etc. No hardcoded colors in component CSS.

## API Integration

All existing API endpoints remain unchanged. The frontend calls:

- `GET /api/settings` -- server status check + settings
- `POST /api/settings` -- save settings
- `GET /api/equipment` -- grinder/brewer lists
- `POST /api/search-coffee` -- AI coffee search
- `POST /api/parse-bag` -- AI bag text parsing
- `POST /api/recommend` -- generate brew recommendation
- `GET /api/presets` -- volume presets
- `POST /api/presets` -- add preset
- `DELETE /api/presets/:id` -- delete preset
- `GET /api/history` -- brew history
- `POST /api/history` -- save brew
- `DELETE /api/history` -- bulk delete history
- `DELETE /api/history/:id` -- delete single brew
- `POST /api/push-aiden` -- push profile to Fellow Aiden
- `GET /api/community-recipes` -- community recipe list
- `POST /api/search-roaster-recipe` -- AI roaster recipe search
- `POST /api/import-brew-link` -- import brew.link profile

The Vite dev server proxies `/api` to `http://localhost:8765` so the Flask backend runs alongside during development. In production, Flask serves the built static files directly.

## Migration Strategy

1. Scaffold the Vite + Preact project in `frontend/` alongside the existing `index.html`
2. Build components incrementally, view by view
3. Once complete, the old `index.html` is deleted
4. Flask's static file serving path points to `frontend/dist/`
5. No backend changes required

## New Feature: Brew Timer

A timer component for manual brew methods.

**State:** elapsed seconds, running/paused/stopped, current step index.

**Behavior:**
- Start begins counting from 0:00
- Display updates every second in `mm:ss` format with tabular-nums font feature
- The step list highlights the current step based on elapsed time vs. step time ranges
- When elapsed time crosses a step boundary, the next step highlights
- Reset returns to 0:00 and clears highlighting
- Timer state is local to the component (not persisted)

**Step-aware highlighting:**
Each brew step has a start time and end time. The timer component receives the steps array and computes which step is active. The active step gets a visual indicator (accent-colored dot on the timeline, slightly bolder text).

**Alerts:**
At step transitions, trigger a subtle notification. On mobile, use `navigator.vibrate(200)` if available. Optionally play a short tone (user can disable in settings if added later).

**Where it appears:**
- Pour-over recipes: below the step list
- AeroPress recipes: below the step list
- Clever Dripper: below the step list
- Aiden: absent
- Simple drip: absent
- Precision drip: absent
