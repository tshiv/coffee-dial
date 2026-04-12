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
