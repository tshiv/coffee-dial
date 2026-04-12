import { useState } from 'preact/hooks';
import { useTheme } from './hooks/useTheme';
import { useApi } from './hooks/useApi';
import { useEquipment } from './hooks/useEquipment';
import { SetupView } from './views/SetupView';
import { InputView } from './views/InputView';
import { RecipeView } from './views/RecipeView';

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

  const handleBack = () => setView('input');
  const handleStartOver = () => {
    setCoffeeData(null);
    setSelectedSize(0);
    setView('input');
  };

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
        <RecipeView
          coffeeData={coffeeData}
          brewOz={selectedSize}
          grinderId={eq.grinderId}
          grinderName={eq.grinderName}
          brewerId={eq.brewerId}
          brewerName={eq.brewerName}
          tempUnit={api.tempUnit}
          apiFetch={api.apiFetch}
          onBack={handleBack}
          onStartOver={handleStartOver}
        />
      )}
      {view === 'settings' && (
        <p style={{ color: 'var(--color-text-muted)' }}>Settings view placeholder</p>
      )}
    </div>
  );
}
