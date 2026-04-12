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
