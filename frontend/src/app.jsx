import { useState } from 'preact/hooks';
import { useTheme } from './hooks/useTheme';
import { useApi } from './hooks/useApi';
import { useEquipment } from './hooks/useEquipment';
import { SetupView } from './views/SetupView';
import { InputView } from './views/InputView';

export function App() {
  const { theme, setTheme } = useTheme();
  const api = useApi();
  const eq = useEquipment(api.apiFetch, api.serverOnline);
  const [view, setView] = useState('input');
  const [coffeeData, setCoffeeData] = useState(null);
  const [selectedSize, setSelectedSize] = useState(0);

  if (!eq.setupComplete) {
    return (
      <div class="app-shell">
        <SetupView equipment={eq.equipment} onComplete={eq.completeSetup} />
      </div>
    );
  }

  return (
    <div class="app-shell">
      {view === 'input' && (
        <InputView
          api={api}
          equipment={eq}
          onNavigate={setView}
          coffeeData={coffeeData}
          setCoffeeData={setCoffeeData}
          selectedSize={selectedSize}
          setSelectedSize={setSelectedSize}
        />
      )}
      {view === 'recipe' && (
        <p style={{ color: 'var(--color-text-muted)' }}>Recipe view placeholder</p>
      )}
      {view === 'settings' && (
        <p style={{ color: 'var(--color-text-muted)' }}>Settings view placeholder</p>
      )}
    </div>
  );
}
