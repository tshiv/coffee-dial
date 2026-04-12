# Coffee Dial Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Coffee Dial frontend from a monolithic HTML file to a Vite + Preact component architecture with warm parchment theme, light/dark mode, two-screen flow, and brew timer.

**Architecture:** Vite scaffolds a new Preact app inside `frontend/`. Components are organized by responsibility (components/, views/, hooks/). CSS Modules with shared design tokens handle theming. The Flask backend is untouched -- Vite proxies `/api` during dev, Flask serves `frontend/dist/` in production.

**Tech Stack:** Vite, Preact, CSS Modules, CSS custom properties for theming

**Spec:** `docs/superpowers/specs/2026-04-09-frontend-redesign-design.md`

---

## File Map

**Create:**
- `frontend/package.json` -- project dependencies
- `frontend/vite.config.js` -- Vite config with API proxy
- `frontend/index.html` -- Vite entry HTML (replaces old index.html)
- `frontend/src/main.jsx` -- App entry point
- `frontend/src/app.jsx` -- Root component with view routing
- `frontend/src/theme/tokens.css` -- CSS custom properties (shared)
- `frontend/src/theme/light.css` -- Light mode overrides
- `frontend/src/theme/dark.css` -- Dark mode overrides
- `frontend/src/theme/global.css` -- Reset, typography, layout
- `frontend/src/hooks/useApi.js` -- Fetch wrapper + server status
- `frontend/src/hooks/useTheme.js` -- Light/dark toggle
- `frontend/src/hooks/useEquipment.js` -- Grinder/brewer state
- `frontend/src/hooks/useTimer.js` -- Brew timer logic
- `frontend/src/lib/format.js` -- Temperature conversion, display helpers
- `frontend/src/components/Header.jsx` + `.module.css`
- `frontend/src/components/CoffeeSearch.jsx` + `.module.css`
- `frontend/src/components/CoffeeIdentity.jsx` + `.module.css`
- `frontend/src/components/SizePicker.jsx` + `.module.css`
- `frontend/src/components/RecipeCard.jsx` + `.module.css`
- `frontend/src/components/AidenProfile.jsx` + `.module.css`
- `frontend/src/components/PourOverSteps.jsx` + `.module.css`
- `frontend/src/components/BrewTimer.jsx` + `.module.css`
- `frontend/src/components/SimpleDrip.jsx` + `.module.css`
- `frontend/src/components/RatingRow.jsx` + `.module.css`
- `frontend/src/views/SetupView.jsx` + `.module.css`
- `frontend/src/views/InputView.jsx` + `.module.css`
- `frontend/src/views/RecipeView.jsx` + `.module.css`
- `frontend/src/views/SettingsView.jsx` + `.module.css`
- `frontend/src/views/HistoryView.jsx` + `.module.css`

**Delete (end of project):**
- `frontend/index.html` (old monolithic file, moved aside during dev)

**Modify:**
- `backend/app.py` -- Update `static_folder` to point to `frontend/dist` (one-line change at end)

---

### Task 1: Scaffold Vite + Preact Project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html` (new Vite entry -- rename old file first)
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/app.jsx`

- [ ] **Step 1: Preserve old frontend**

```bash
cd frontend
mv index.html index.old.html
```

- [ ] **Step 2: Create package.json**

```json
{
  "name": "coffee-dial",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "preact": "^10.25.0"
  },
  "devDependencies": {
    "@preact/preset-vite": "^2.9.0",
    "vite": "^6.0.0"
  }
}
```

- [ ] **Step 3: Create vite.config.js**

```js
import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';

export default defineConfig({
  plugins: [preact()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8765',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
```

- [ ] **Step 4: Create Vite entry HTML**

Write `frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Coffee Dial</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create main.jsx entry point**

Write `frontend/src/main.jsx`:

```jsx
import { render } from 'preact';
import { App } from './app';
import './theme/global.css';
import './theme/tokens.css';

render(<App />, document.getElementById('app'));
```

- [ ] **Step 6: Create app.jsx shell**

Write `frontend/src/app.jsx`:

```jsx
import { useState } from 'preact/hooks';

export function App() {
  const [view, setView] = useState('input');

  return (
    <div class="app-shell">
      <p>Coffee Dial — {view}</p>
      <button onClick={() => setView('settings')}>Settings</button>
      <button onClick={() => setView('input')}>Home</button>
    </div>
  );
}
```

- [ ] **Step 7: Install dependencies and verify dev server starts**

```bash
cd frontend
npm install
npm run dev
```

Expected: Vite dev server starts on http://localhost:5173, shows "Coffee Dial — input" text.

- [ ] **Step 8: Verify build works**

```bash
cd frontend
npm run build
ls dist/
```

Expected: `dist/` directory contains `index.html` and `assets/` with JS/CSS bundles.

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/vite.config.js frontend/index.html frontend/src/ frontend/index.old.html
echo "node_modules\ndist" >> frontend/.gitignore
git add frontend/.gitignore
git commit -m "feat: scaffold Vite + Preact project alongside existing frontend"
```

---

### Task 2: Theme System (Design Tokens + Light/Dark)

**Files:**
- Create: `frontend/src/theme/tokens.css`
- Create: `frontend/src/theme/light.css`
- Create: `frontend/src/theme/dark.css`
- Create: `frontend/src/theme/global.css`
- Create: `frontend/src/hooks/useTheme.js`

- [ ] **Step 1: Create tokens.css with CSS custom properties**

Write `frontend/src/theme/tokens.css`:

```css
:root {
  --color-bg: #FAF7F2;
  --color-surface: #F3EDE4;
  --color-border: #E4D9CB;
  --color-text: #2C1E12;
  --color-text-secondary: #6B5744;
  --color-text-muted: #9B8B7A;
  --color-accent: #C8854A;
  --color-cta-bg: #3C2A1A;
  --color-cta-text: #F3EDE4;
  --color-tag-bg: #E8DFD1;
  --color-tag-text: #6B5744;
  --color-green: #6ab87a;
  --color-red: #c86a5a;
  --color-yellow: #d4a84b;

  --radius: 10px;
  --radius-sm: 6px;
  --radius-lg: 12px;

  --font-sans: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;

  --max-width: 520px;
}
```

- [ ] **Step 2: Create dark.css overrides**

Write `frontend/src/theme/dark.css`:

```css
[data-theme="dark"] {
  --color-bg: #1A1714;
  --color-surface: #241F1A;
  --color-border: #2E271F;
  --color-text: #F0E6D8;
  --color-text-secondary: #A89880;
  --color-text-muted: #7A6B5A;
  --color-accent: #C8854A;
  --color-cta-bg: #C8854A;
  --color-cta-text: #1A1714;
  --color-tag-bg: #2E271F;
  --color-tag-text: #A89880;
}
```

- [ ] **Step 3: Create light.css (explicit, for system-preference matching)**

Write `frontend/src/theme/light.css`:

```css
[data-theme="light"] {
  /* Light is the default in tokens.css, but we declare explicitly
     so system-preference media queries can reference it. */
}

@media (prefers-color-scheme: dark) {
  [data-theme="system"] {
    --color-bg: #1A1714;
    --color-surface: #241F1A;
    --color-border: #2E271F;
    --color-text: #F0E6D8;
    --color-text-secondary: #A89880;
    --color-text-muted: #7A6B5A;
    --color-accent: #C8854A;
    --color-cta-bg: #C8854A;
    --color-cta-text: #1A1714;
    --color-tag-bg: #2E271F;
    --color-tag-text: #A89880;
  }
}
```

- [ ] **Step 4: Create global.css with reset and base typography**

Write `frontend/src/theme/global.css`:

```css
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  background: var(--color-bg);
  color: var(--color-text);
  min-height: 100vh;
  min-height: 100dvh;
  line-height: 1.5;
  font-size: 14px;
}

.app-shell {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 20px 16px 40px;
}

input, select, textarea, button {
  font-family: inherit;
  font-size: inherit;
}

a { color: var(--color-accent); text-decoration: none; }
a:hover { text-decoration: underline; }
```

- [ ] **Step 5: Create useTheme hook**

Write `frontend/src/hooks/useTheme.js`:

```js
import { useState, useEffect } from 'preact/hooks';

const STORAGE_KEY = 'cd_theme';

export function useTheme() {
  const [theme, setThemeState] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) || 'system';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const setTheme = (newTheme) => {
    setThemeState(newTheme);
  };

  return { theme, setTheme };
}
```

- [ ] **Step 6: Import theme files in main.jsx**

Update `frontend/src/main.jsx`:

```jsx
import { render } from 'preact';
import { App } from './app';
import './theme/tokens.css';
import './theme/light.css';
import './theme/dark.css';
import './theme/global.css';

render(<App />, document.getElementById('app'));
```

- [ ] **Step 7: Wire useTheme into App and verify**

Update `frontend/src/app.jsx`:

```jsx
import { useState } from 'preact/hooks';
import { useTheme } from './hooks/useTheme';

export function App() {
  const { theme, setTheme } = useTheme();
  const [view, setView] = useState('input');

  return (
    <div class="app-shell">
      <h1 style={{ color: 'var(--color-text)', fontSize: '22px', fontWeight: 700 }}>Coffee Dial</h1>
      <p style={{ color: 'var(--color-text-muted)', fontSize: '13px' }}>Theme: {theme}</p>
      <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
        <button onClick={() => setTheme('light')}>Light</button>
        <button onClick={() => setTheme('dark')}>Dark</button>
        <button onClick={() => setTheme('system')}>System</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 8: Verify visually**

Run `npm run dev`, open http://localhost:5173. Click Light/Dark/System buttons. Background should switch between parchment (#FAF7F2) and dark roast (#1A1714). Text colors should follow.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/theme/ frontend/src/hooks/useTheme.js frontend/src/main.jsx frontend/src/app.jsx
git commit -m "feat: add theme system with light/dark/system modes and warm parchment palette"
```

---

### Task 3: Core Hooks (useApi, useEquipment, format helpers)

**Files:**
- Create: `frontend/src/hooks/useApi.js`
- Create: `frontend/src/hooks/useEquipment.js`
- Create: `frontend/src/lib/format.js`

- [ ] **Step 1: Create useApi hook**

Write `frontend/src/hooks/useApi.js`:

```js
import { useState, useEffect, useCallback } from 'preact/hooks';

export function useApi() {
  const [serverOnline, setServerOnline] = useState(false);
  const [tempUnit, setTempUnit] = useState('F');

  const checkServer = useCallback(async () => {
    try {
      const r = await fetch('/api/settings', { signal: AbortSignal.timeout(3000) });
      if (r.ok) {
        setServerOnline(true);
        const s = await r.json();
        setTempUnit(s.temp_unit || 'F');
      } else {
        setServerOnline(false);
      }
    } catch {
      setServerOnline(false);
    }
  }, []);

  useEffect(() => {
    checkServer();
    const interval = setInterval(checkServer, 15000);
    return () => clearInterval(interval);
  }, [checkServer]);

  const apiFetch = useCallback(async (path, options = {}) => {
    const r = await fetch('/api' + path, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Request failed');
    return data;
  }, []);

  return { serverOnline, tempUnit, setTempUnit, apiFetch, checkServer };
}
```

- [ ] **Step 2: Create useEquipment hook**

Write `frontend/src/hooks/useEquipment.js`:

```js
import { useState, useEffect, useCallback } from 'preact/hooks';

export function useEquipment(apiFetch, serverOnline) {
  const [equipment, setEquipment] = useState({ grinders: [], brewers: [] });
  const [grinderId, setGrinderId] = useState(() => localStorage.getItem('cd_grinder') || '');
  const [brewerId, setBrewerId] = useState(() => localStorage.getItem('cd_brewer') || '');
  const [setupComplete, setSetupComplete] = useState(() => localStorage.getItem('cd_setup_complete') === '1');

  const loadEquipment = useCallback(async () => {
    if (!serverOnline) return;
    try {
      const data = await apiFetch('/equipment');
      setEquipment(data);
    } catch {
      // Server offline or error
    }
  }, [apiFetch, serverOnline]);

  useEffect(() => { loadEquipment(); }, [loadEquipment]);

  const selectGrinder = (id) => {
    setGrinderId(id);
    localStorage.setItem('cd_grinder', id);
  };

  const selectBrewer = (id) => {
    setBrewerId(id);
    localStorage.setItem('cd_brewer', id);
  };

  const completeSetup = (gId, bId) => {
    selectGrinder(gId);
    selectBrewer(bId);
    localStorage.setItem('cd_setup_complete', '1');
    setSetupComplete(true);
  };

  const grinderName = equipment.grinders.find(g => g.id === grinderId)?.name || '';
  const brewerName = equipment.brewers.find(b => b.id === brewerId)?.name || '';

  return {
    equipment,
    grinderId, brewerId,
    grinderName, brewerName,
    selectGrinder, selectBrewer,
    setupComplete, completeSetup,
    loadEquipment,
  };
}
```

- [ ] **Step 3: Create format helpers**

Write `frontend/src/lib/format.js`:

```js
export function fmtTemp(tempC, tempF, unit) {
  return unit === 'C' ? `${tempC}\u00B0C` : `${tempF}\u00B0F`;
}

export function fmtTempValue(tempC, tempF, unit) {
  return unit === 'C' ? tempC : tempF;
}

export function cToF(c) {
  return Math.round(c * 9 / 5 + 32);
}

export function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}
```

- [ ] **Step 4: Verify hooks load by wiring into App temporarily**

Update `frontend/src/app.jsx`:

```jsx
import { useState } from 'preact/hooks';
import { useTheme } from './hooks/useTheme';
import { useApi } from './hooks/useApi';
import { useEquipment } from './hooks/useEquipment';

export function App() {
  const { theme, setTheme } = useTheme();
  const { serverOnline, tempUnit, apiFetch } = useApi();
  const { equipment, grinderName, brewerName, setupComplete } = useEquipment(apiFetch, serverOnline);

  return (
    <div class="app-shell">
      <h1 style={{ color: 'var(--color-text)', fontSize: '22px', fontWeight: 700 }}>Coffee Dial</h1>
      <p style={{ color: 'var(--color-text-muted)', fontSize: '13px' }}>
        Server: {serverOnline ? 'online' : 'offline'} | Theme: {theme} | Temp: {tempUnit}
      </p>
      <p style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>
        {grinderName || '(no grinder)'} · {brewerName || '(no brewer)'} | Setup: {setupComplete ? 'done' : 'needed'}
      </p>
      <p style={{ color: 'var(--color-text-muted)', fontSize: '12px' }}>
        {equipment.grinders.length} grinders, {equipment.brewers.length} brewers loaded
      </p>
    </div>
  );
}
```

- [ ] **Step 5: Verify with dev server running alongside Flask backend**

Start Flask backend on 8765, then `cd frontend && npm run dev`. Open http://localhost:5173. Should show server online, equipment counts, and grinder/brewer names if previously set.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useApi.js frontend/src/hooks/useEquipment.js frontend/src/lib/format.js frontend/src/app.jsx
git commit -m "feat: add useApi, useEquipment hooks and format helpers"
```

---

### Task 4: Header Component

**Files:**
- Create: `frontend/src/components/Header.jsx`
- Create: `frontend/src/components/Header.module.css`

- [ ] **Step 1: Create Header.module.css**

Write `frontend/src/components/Header.module.css`:

```css
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  margin-bottom: 6px;
}

.left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo {
  width: 28px;
  height: 28px;
  background: var(--color-cta-bg);
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logoMark {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--color-accent);
}

.title {
  font-size: 19px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.3px;
}

.right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.equipment {
  font-size: 11px;
  color: var(--color-text-muted);
}

.gearBtn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: none;
  color: var(--color-text-muted);
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}

.gearBtn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
```

- [ ] **Step 2: Create Header.jsx**

Write `frontend/src/components/Header.jsx`:

```jsx
import styles from './Header.module.css';

export function Header({ grinderName, brewerName, onGearClick }) {
  const equipmentText = [grinderName, brewerName].filter(Boolean).join(' \u00B7 ');

  return (
    <header class={styles.header}>
      <div class={styles.left}>
        <div class={styles.logo}>
          <div class={styles.logoMark} />
        </div>
        <span class={styles.title}>Coffee Dial</span>
      </div>
      <div class={styles.right}>
        {equipmentText && <span class={styles.equipment}>{equipmentText}</span>}
        <button class={styles.gearBtn} onClick={onGearClick} title="Settings">
          &#9881;
        </button>
      </div>
    </header>
  );
}
```

- [ ] **Step 3: Wire Header into App to verify**

Update `app.jsx` to render `<Header>` instead of the inline debug text. Verify the logo, title, equipment text, and gear icon render correctly.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Header.jsx frontend/src/components/Header.module.css frontend/src/app.jsx
git commit -m "feat: add Header component with logo, equipment context, gear icon"
```

---

### Task 5: SetupView

**Files:**
- Create: `frontend/src/views/SetupView.jsx`
- Create: `frontend/src/views/SetupView.module.css`

- [ ] **Step 1: Create SetupView.module.css**

Write `frontend/src/views/SetupView.module.css`:

```css
.setup {
  text-align: center;
  padding-top: 80px;
}

.logoBig {
  width: 56px;
  height: 56px;
  background: var(--color-cta-bg);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
}

.logoBigMark {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 3px solid var(--color-accent);
}

.title {
  font-size: 24px;
  font-weight: 800;
  color: var(--color-text);
  letter-spacing: -0.5px;
  margin-bottom: 6px;
}

.subtitle {
  font-size: 14px;
  color: var(--color-text-muted);
  margin-bottom: 36px;
}

.field {
  text-align: left;
  margin-bottom: 20px;
}

.label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  letter-spacing: 0.3px;
  margin-bottom: 6px;
}

.select {
  width: 100%;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text);
  font-size: 14px;
  padding: 10px 12px;
  appearance: none;
}

.select:focus {
  outline: none;
  border-color: var(--color-accent);
}

.cta {
  width: 100%;
  background: var(--color-cta-bg);
  color: var(--color-cta-text);
  border: none;
  border-radius: var(--radius);
  padding: 14px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 12px;
  transition: opacity 0.15s;
}

.cta:hover {
  opacity: 0.9;
}
```

- [ ] **Step 2: Create SetupView.jsx**

Write `frontend/src/views/SetupView.jsx`:

```jsx
import { useState } from 'preact/hooks';
import styles from './SetupView.module.css';

export function SetupView({ equipment, onComplete }) {
  const [grinderId, setGrinderId] = useState(equipment.grinders[0]?.id || '');
  const [brewerId, setBrewerId] = useState(equipment.brewers[0]?.id || '');

  const handleSubmit = () => {
    if (grinderId && brewerId) {
      onComplete(grinderId, brewerId);
    }
  };

  const renderOptions = (items, type) => {
    const groups = type === 'grinder'
      ? [['electric', 'Electric'], ['manual', 'Manual']]
      : [['automatic', 'Automatic'], ['manual', 'Manual']];

    return groups.map(([key, label]) => {
      const filtered = items.filter(item => item.type === key);
      if (!filtered.length) return null;
      return (
        <optgroup label={label} key={key}>
          {filtered.map(item => (
            <option value={item.id} key={item.id}>{item.name}</option>
          ))}
        </optgroup>
      );
    });
  };

  return (
    <div class={styles.setup}>
      <div class={styles.logoBig}>
        <div class={styles.logoBigMark} />
      </div>
      <h2 class={styles.title}>Coffee Dial</h2>
      <p class={styles.subtitle}>Pick your grinder and brewer to get started.</p>

      <div class={styles.field}>
        <label class={styles.label}>Grinder</label>
        <select
          class={styles.select}
          value={grinderId}
          onChange={e => setGrinderId(e.target.value)}
        >
          {renderOptions(equipment.grinders, 'grinder')}
        </select>
      </div>

      <div class={styles.field}>
        <label class={styles.label}>Brewer</label>
        <select
          class={styles.select}
          value={brewerId}
          onChange={e => setBrewerId(e.target.value)}
        >
          {renderOptions(equipment.brewers, 'brewer')}
        </select>
      </div>

      <button class={styles.cta} onClick={handleSubmit}>Let's Brew</button>
    </div>
  );
}
```

- [ ] **Step 3: Wire SetupView into App routing**

Update `frontend/src/app.jsx` to show `SetupView` when `!setupComplete`, otherwise show the header + placeholder for InputView.

```jsx
import { useState } from 'preact/hooks';
import { useTheme } from './hooks/useTheme';
import { useApi } from './hooks/useApi';
import { useEquipment } from './hooks/useEquipment';
import { Header } from './components/Header';
import { SetupView } from './views/SetupView';

export function App() {
  const { theme, setTheme } = useTheme();
  const { serverOnline, tempUnit, apiFetch } = useApi();
  const eq = useEquipment(apiFetch, serverOnline);
  const [view, setView] = useState('input');

  if (!eq.setupComplete) {
    return (
      <div class="app-shell">
        <SetupView equipment={eq.equipment} onComplete={eq.completeSetup} />
      </div>
    );
  }

  return (
    <div class="app-shell">
      <Header
        grinderName={eq.grinderName}
        brewerName={eq.brewerName}
        onGearClick={() => setView('settings')}
      />
      <p style={{ color: 'var(--color-text-muted)' }}>View: {view}</p>
    </div>
  );
}
```

- [ ] **Step 4: Verify setup flow**

Clear localStorage (`localStorage.clear()` in console), refresh. Setup screen should appear with equipment dropdowns. Click "Let's Brew" -- should transition to the main app with header. Refresh -- should stay on main app (setup is complete).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/SetupView.jsx frontend/src/views/SetupView.module.css frontend/src/app.jsx
git commit -m "feat: add SetupView with first-run grinder/brewer selection"
```

---

### Task 6: CoffeeSearch + CoffeeIdentity Components

**Files:**
- Create: `frontend/src/components/CoffeeSearch.jsx` + `.module.css`
- Create: `frontend/src/components/CoffeeIdentity.jsx` + `.module.css`

- [ ] **Step 1: Create CoffeeSearch component**

CoffeeSearch handles the search/paste toggle, input field, AI status spinner, and error display. It calls `onResult(coffeeData)` when coffee is detected.

Write `CoffeeSearch.module.css` with styles for the section label, toggle tabs, search row (input + button), paste textarea, spinner, and error box. Follow the warm parchment palette -- input backgrounds use `var(--color-surface)`, borders use `var(--color-border)`.

Write `CoffeeSearch.jsx`:
- State: `mode` ('search' | 'paste'), `query`, `bagText`, `loading`, `error`
- Search mode: input + "Search" button, Enter key submits
- Paste mode: textarea + "Parse with AI" button
- Loading state: spinner + status text
- Error state: error text in accent red
- On success: calls `onResult(data)` prop

- [ ] **Step 2: Create CoffeeIdentity component**

CoffeeIdentity displays the detected coffee. It receives `coffeeData` as a prop and renders nothing if null.

Write `CoffeeIdentity.module.css` with styles for the identity block. Coffee name is 20px weight 700, roaster line is 13px secondary color, tags use `var(--color-tag-bg)` and `var(--color-tag-text)`, tasting notes are 12px italic muted.

Write `CoffeeIdentity.jsx`:
- Props: `coffeeData` (null or object with coffee_name, roaster, roast, origin, process, variety, flavor_notes, confidence, reasoning)
- Renders: name + roaster, confidence badge, roast/origin/process tags, flavor notes in italics, AI reasoning in smaller muted text
- Returns null if `coffeeData` is null

- [ ] **Step 3: Verify by wiring into App temporarily**

Add both components to the app shell. Search for a coffee, verify the identity block appears with proper styling.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/CoffeeSearch.* frontend/src/components/CoffeeIdentity.*
git commit -m "feat: add CoffeeSearch and CoffeeIdentity components"
```

---

### Task 7: SizePicker Component

**Files:**
- Create: `frontend/src/components/SizePicker.jsx` + `.module.css`

- [ ] **Step 1: Create SizePicker**

Displays preset cards (from `/api/presets`) as tappable buttons + a custom oz input row. Selected state uses `var(--color-cta-bg)` background with `var(--color-cta-text)` text.

Write `SizePicker.module.css`: grid layout for preset cards (`grid-template-columns: repeat(auto-fill, minmax(100px, 1fr))`), each card has name (14px weight 600), oz value (18px weight 800 accent color), "oz" unit label. Custom row is a flex row with "Custom" label, number input (70px wide), and "oz" text.

Write `SizePicker.jsx`:
- Props: `presets`, `selectedId`, `customOz`, `onSelect(id, oz)`, `onCustom(oz)`
- Renders preset cards, highlights selected
- Custom row: clicking it or typing in the input selects custom mode

- [ ] **Step 2: Verify with mock presets**

Wire into app with hardcoded presets array. Verify card selection, custom input, and selected state styling.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SizePicker.*
git commit -m "feat: add SizePicker component with preset cards and custom input"
```

---

### Task 8: InputView (Screen 1)

**Files:**
- Create: `frontend/src/views/InputView.jsx` + `.module.css`

- [ ] **Step 1: Create InputView**

Composes Header, CoffeeSearch, CoffeeIdentity, SizePicker, and the CTA button into screen 1.

Write `InputView.module.css`: styles for the offline banner, the CTA button ("Get my recipe" with arrow), disabled state at 0.4 opacity.

Write `InputView.jsx`:
- Props: `api` (useApi return), `equipment` (useEquipment return), `onNavigate(view)`, `coffeeData`/`setCoffeeData`, `selectedSize`/`setSelectedSize`
- Loads presets from API on mount
- Renders: Header, offline banner (if server down), CoffeeSearch, CoffeeIdentity, SizePicker, CTA button
- CTA disabled until `coffeeData` is truthy and a size is selected
- CTA click calls `onNavigate('recipe')`

- [ ] **Step 2: Wire InputView into App as the default view**

Update `app.jsx`: lift `coffeeData` and `selectedSize` state to App. Render InputView when `view === 'input'`.

- [ ] **Step 3: Verify full input flow**

Search for a coffee, select a size, verify the CTA enables. Click it -- should switch to recipe view (placeholder for now).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/InputView.* frontend/src/app.jsx
git commit -m "feat: add InputView composing search, coffee identity, and size picker"
```

---

### Task 9: RecipeCard + SimpleDrip + AidenProfile Components

**Files:**
- Create: `frontend/src/components/RecipeCard.jsx` + `.module.css`
- Create: `frontend/src/components/SimpleDrip.jsx` + `.module.css`
- Create: `frontend/src/components/AidenProfile.jsx` + `.module.css`

- [ ] **Step 1: Create RecipeCard component**

The key-value recipe list. This is the core of the recipe view.

Write `RecipeCard.module.css`: each row is a flex row with `justify-content: space-between`, label in 13px muted, value in 17px weight 700. Rows separated by `border-bottom: 1px solid var(--color-border)` on a lighter shade. Last row has no border.

Write `RecipeCard.jsx`:
- Props: `rec` (recommendation object from API), `tempUnit`
- Renders: grind setting, water temperature, coffee dose, water amount, ratio
- Uses `fmtTemp()` from format.js for temperature display
- Learning note (if `rec.bias_notes` contains a "History:" note): yellow-tinted box below the list

- [ ] **Step 2: Create AidenProfile component**

Write `AidenProfile.module.css`: 3-column grid with surface background, profile name input, push button.

Write `AidenProfile.jsx`:
- Props: `recipe`, `tempUnit`, `coffeeName`, `apiFetch`
- Renders: bloom time, bloom ratio, pulses, pulse interval, temperature, ratio in a grid
- Profile name input, "Push to Aiden" button
- Push status states: idle, loading (spinner), success, error

- [ ] **Step 3: Create SimpleDrip component**

Write `SimpleDrip.jsx`:
- Props: `recipe`
- Renders: single paragraph with dose, water amount, and any note
- Minimal -- just a `<p>` with the brew instructions

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/RecipeCard.* frontend/src/components/AidenProfile.* frontend/src/components/SimpleDrip.*
git commit -m "feat: add RecipeCard, AidenProfile, and SimpleDrip components"
```

---

### Task 10: PourOverSteps + BrewTimer Components

**Files:**
- Create: `frontend/src/components/PourOverSteps.jsx` + `.module.css`
- Create: `frontend/src/components/BrewTimer.jsx` + `.module.css`
- Create: `frontend/src/hooks/useTimer.js`

- [ ] **Step 1: Create useTimer hook**

Write `frontend/src/hooks/useTimer.js`:

```js
import { useState, useEffect, useRef, useCallback } from 'preact/hooks';

export function useTimer(steps) {
  const [elapsed, setElapsed] = useState(0);
  const [running, setRunning] = useState(false);
  const intervalRef = useRef(null);
  const prevStepRef = useRef(-1);

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => {
        setElapsed(e => e + 1);
      }, 1000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [running]);

  // Compute active step index from elapsed time
  let activeStep = -1;
  if (steps && steps.length && elapsed > 0) {
    let cumulative = 0;
    for (let i = 0; i < steps.length; i++) {
      const dur = steps[i].duration_s || 0;
      if (elapsed <= cumulative + dur || i === steps.length - 1) {
        activeStep = i;
        break;
      }
      cumulative += dur;
    }
  }

  // Vibrate on step change
  useEffect(() => {
    if (activeStep !== prevStepRef.current && activeStep >= 0 && running) {
      prevStepRef.current = activeStep;
      if (navigator.vibrate) {
        navigator.vibrate(200);
      }
    }
  }, [activeStep, running]);

  const start = useCallback(() => setRunning(true), []);
  const pause = useCallback(() => setRunning(false), []);
  const reset = useCallback(() => {
    setRunning(false);
    setElapsed(0);
    prevStepRef.current = -1;
  }, []);

  return { elapsed, running, activeStep, start, pause, reset };
}
```

- [ ] **Step 2: Create PourOverSteps component**

Write `PourOverSteps.module.css`: vertical timeline rail (2px border-left on the container, positioned dots for each step in accent color, active step dot is larger or filled differently). Step rows show action name, instruction text, time range. Active step gets accent-colored text or bolder weight.

Write `PourOverSteps.jsx`:
- Props: `recipe` (with `steps` array and optionally `target_total_time_s` or `steep_time_s`), `activeStep` (from useTimer)
- Renders each step with: step dot, action label (uppercase, accent color), instruction note, time range
- Active step gets a visual highlight (accent dot filled vs outline, or background tint)
- Shows total time below

- [ ] **Step 3: Create BrewTimer component**

Write `BrewTimer.module.css`: centered layout, large timer display (36px, weight 700, tabular-nums), Start/Reset buttons.

Write `BrewTimer.jsx`:
- Props: `elapsed`, `running`, `onStart`, `onPause`, `onReset`
- Renders: `formatTime(elapsed)` in large text
- Start button (or Pause if running), Reset button
- Start: `var(--color-cta-bg)` background. Reset: outline style.

- [ ] **Step 4: Verify timer works standalone**

Wire BrewTimer into app temporarily with mock steps. Start timer, verify it counts up, verify step highlighting changes at boundaries, verify reset clears.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useTimer.js frontend/src/components/PourOverSteps.* frontend/src/components/BrewTimer.*
git commit -m "feat: add PourOverSteps, BrewTimer components and useTimer hook"
```

---

### Task 11: RatingRow Component

**Files:**
- Create: `frontend/src/components/RatingRow.jsx` + `.module.css`

- [ ] **Step 1: Create RatingRow**

Write `RatingRow.module.css`: four flex buttons with `var(--color-surface)` background, border, hover and selected states matching the palette.

Write `RatingRow.jsx`:
- Props: `onSave(rating)`, `apiFetch`, `brewData` (the full brew entry to save)
- State: `selectedRating`, `saveStatus` (idle, saving, saved)
- Four buttons: Too Bitter, Too Bright, Flat/Weak, Just Right
- "Save to History" button appears after selection
- Calls `POST /api/history` with the brew entry + selected rating

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/RatingRow.*
git commit -m "feat: add RatingRow component for post-brew feedback"
```

---

### Task 12: RecipeView (Screen 2)

**Files:**
- Create: `frontend/src/views/RecipeView.jsx` + `.module.css`

- [ ] **Step 1: Create RecipeView**

This is the output screen. Composes all recipe components based on brewer type.

Write `RecipeView.module.css`: back link styles, coffee-as-page-title styles (24px weight 800, -0.5px letter-spacing), context line, divider, "Brew something else" button at bottom.

Write `RecipeView.jsx`:
- Props: `coffeeData`, `rec` (recommendation), `brewOz`, `grinderName`, `brewerName`, `brewerId`, `tempUnit`, `apiFetch`, `onBack`, `onStartOver`
- Calls `/api/recommend` on mount (or receives pre-fetched rec)
- Renders:
  - Back link ("Change coffee")
  - Coffee name as page title (24px bold)
  - Roaster, origin, roast, tasting notes
  - Context line: "Brewing {oz}oz on {grinderName} > {brewerName}"
  - Divider
  - RecipeCard (key-value list)
  - Brewer-specific section:
    - If `recipe.type === 'aiden_profile'`: AidenProfile
    - If `recipe.type === 'pour_over_steps'` or `'aeropress_steps'`: PourOverSteps + BrewTimer
    - If `recipe.type === 'simple_drip'`: SimpleDrip
    - If `recipe.type === 'precision_drip'`: grid similar to Aiden but without push
  - Learning note (if applicable)
  - RatingRow
  - "Brew something else" button

- [ ] **Step 2: Wire RecipeView into App**

Update `app.jsx`: when CTA is clicked on InputView, call `/api/recommend` and pass the result to RecipeView. Lift recommendation state to App.

- [ ] **Step 3: Verify full flow end-to-end**

Search coffee on InputView, pick size, click "Get my recipe". RecipeView should show with the coffee as page title, key-value recipe list, brewer-specific section. Back link should return to InputView with state preserved. "Brew something else" should clear and restart.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/RecipeView.* frontend/src/app.jsx
git commit -m "feat: add RecipeView with brewer-adaptive recipe display"
```

---

### Task 13: SettingsView + HistoryView

**Files:**
- Create: `frontend/src/views/SettingsView.jsx` + `.module.css`
- Create: `frontend/src/views/HistoryView.jsx` + `.module.css`

- [ ] **Step 1: Create SettingsView**

Write `SettingsView.module.css`: settings header with "Done" button, card containers, settings rows (label left, control right), dividers.

Write `SettingsView.jsx`:
- Props: `api`, `equipment`, `theme`/`setTheme`, `onDone`, `onViewHistory`
- Sections: Equipment, Volume Presets, AI Provider + Key, Temperature Unit, Theme Toggle (light/dark/system), Fellow Credentials, Brew History (count + View button + Clear), Backend Status, About
- Each section in a card-like container
- "Done" button returns to previous view

- [ ] **Step 2: Create HistoryView**

Write `HistoryView.module.css`: header with "Done" button, brew entry cards.

Write `HistoryView.jsx`:
- Props: `apiFetch`, `onDone`
- Loads history from `/api/history` on mount
- Renders chronological list: date, coffee name, roast/origin, grind setting, volume, dose, rating
- Empty state: "No brews yet."

- [ ] **Step 3: Wire both views into App routing**

Update `app.jsx` to handle `view === 'settings'` and `view === 'history'`. Track `previousView` so "Done" returns correctly.

- [ ] **Step 4: Verify settings flow**

Click gear icon, settings opens. Change theme, verify it applies. Click "Done", returns to previous screen. Navigate to history from settings, verify entries load, "Done" returns to settings.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/SettingsView.* frontend/src/views/HistoryView.* frontend/src/app.jsx
git commit -m "feat: add SettingsView and HistoryView"
```

---

### Task 14: Community Recipes + Brew Link Import

**Files:**
- Modify: `frontend/src/views/RecipeView.jsx`

- [ ] **Step 1: Add community recipes section to RecipeView**

Below the brewer-specific section, add:
- Community recipes list (loaded from `/api/community-recipes?brewer_id=...`)
- Each recipe card: title, author, params grid (ratio, temp, dose, time), "Use This Recipe" button
- Roaster recipe search input + button (calls `/api/search-roaster-recipe`)
- Brew.link import input (Aiden only, calls `/api/import-brew-link`)

Reuse the existing data patterns from the old frontend but render with Preact components.

- [ ] **Step 2: Verify community recipes load for different brewers**

Test with Aiden (should show push buttons on community recipes), V60 (should show step-based recipes), Moccamaster (may have few/no community recipes).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/RecipeView.jsx
git commit -m "feat: add community recipes, roaster search, and brew.link import to RecipeView"
```

---

### Task 15: Build Integration + Cleanup

**Files:**
- Modify: `backend/app.py` (one line)
- Delete: `frontend/index.old.html`
- Update: `frontend/.gitignore`
- Update: `.claude/launch.json`

- [ ] **Step 1: Update Flask static folder**

In `backend/app.py`, update the `Flask` constructor to point to the built frontend:

Change:
```python
app = Flask(__name__, static_folder=FRONTEND_DIR)
```
To:
```python
app = Flask(__name__, static_folder=os.path.join(FRONTEND_DIR, "dist"))
```

And update the catch-all route to serve from dist:
```python
@app.route("/")
def index():
    return send_from_directory(os.path.join(FRONTEND_DIR, "dist"), "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(os.path.join(FRONTEND_DIR, "dist"), path)
```

- [ ] **Step 2: Build and verify production serving**

```bash
cd frontend
npm run build
cd ../backend
python app.py
```

Open http://localhost:8765. The new Preact app should load, served by Flask.

- [ ] **Step 3: Delete old frontend**

```bash
rm frontend/index.old.html
```

- [ ] **Step 4: Update launch.json for dev workflow**

Update `.claude/launch.json`:

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "Coffee Dial Frontend",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "port": 5173,
      "cwd": "frontend"
    },
    {
      "name": "Coffee Dial Backend",
      "runtimeExecutable": "python3",
      "runtimeArgs": ["app.py"],
      "port": 8765,
      "cwd": "backend"
    }
  ]
}
```

- [ ] **Step 5: Verify full end-to-end**

Start Flask backend. Run `cd frontend && npm run build`. Open http://localhost:8765. Verify:
- Setup screen works (clear localStorage to test)
- Coffee search + detection works
- Size picker works
- Recipe view renders correctly for Aiden brewer
- Settings view works (theme toggle, equipment change)
- History view works
- Light/dark mode works
- Mobile viewport looks correct

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete frontend rebuild - delete old monolith, wire Flask to dist"
```
