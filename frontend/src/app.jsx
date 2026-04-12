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
