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
