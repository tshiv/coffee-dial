import { useState } from 'preact/hooks';
import { useTheme } from './hooks/useTheme';
import { useApi } from './hooks/useApi';
import { useEquipment } from './hooks/useEquipment';
import { useBags } from './hooks/useBags';
import { bagToCoffee } from './lib/freshness';
import { SetupView } from './views/SetupView';
import { InputView } from './views/InputView';
import { RecipeView } from './views/RecipeView';
import { SettingsView } from './views/SettingsView';
import { HistoryView } from './views/HistoryView';
import { AidenProfilesView } from './views/AidenProfilesView';

export function App() {
  const { theme, setTheme } = useTheme();
  const api = useApi();
  const eq = useEquipment(api.apiFetch, api.serverOnline);
  const bags = useBags(api.apiFetch, api.serverOnline);
  const [view, setView] = useState('input');
  const [previousView, setPreviousView] = useState('input');
  const [coffeeData, setCoffeeData] = useState(null);
  const [selectedSize, setSelectedSize] = useState(0);
  const [selectedBagId, setSelectedBagId] = useState(null);
  const [continueChain, setContinueChain] = useState(true);
  // Set by "brew again" on the recipe screen; otherwise the parent is derived
  // from the selected bag's last rated brew.
  const [parentOverride, setParentOverride] = useState(null);

  const selectedBag = bags.bags.find(b => b.id === selectedBagId) || null;
  const lastRated = selectedBag?.last_brew?.rating ? selectedBag.last_brew : null;
  const parentBrewId = parentOverride ?? (continueChain && lastRated ? lastRated.id : null);

  if (!eq.setupComplete) {
    return (
      <div class="app-shell">
        <SetupView equipment={eq.equipment} onComplete={eq.completeSetup} />
      </div>
    );
  }

  // Remember where Settings was opened from, so Done returns there. Views
  // reached from inside Settings (history, profiles) must not overwrite it,
  // or Done would loop back to Settings forever.
  const navigate = (target) => {
    if (target === 'settings') setPreviousView(view);
    setView(target);
  };

  const selectBag = (bag) => {
    setSelectedBagId(bag ? bag.id : null);
    setCoffeeData(bag ? bagToCoffee(bag) : null);
    setParentOverride(null);
    setContinueChain(true);
  };

  const setCoffeeFromSearch = (data) => {
    setCoffeeData(data);
    setSelectedBagId(null);
    setParentOverride(null);
  };

  const handleBack = () => {
    setParentOverride(null);
    bags.load();
    setView('input');
  };

  const handleStartOver = () => {
    setCoffeeData(null);
    setSelectedSize(0);
    setSelectedBagId(null);
    setParentOverride(null);
    bags.load();
    setView('input');
  };

  // The rated brew becomes the parent of the next one. The recipe view is
  // keyed on the parent, so this remounts it with a fresh recommendation.
  const handleBrewAgain = (brewId) => {
    setParentOverride(brewId);
    bags.load();
    setView('recipe');
  };

  return (
    <div class="app-shell">
      {view === 'input' && (
        <InputView
          api={api}
          equipment={eq}
          bags={bags}
          selectedBag={selectedBag}
          onSelectBag={selectBag}
          continueChain={continueChain}
          setContinueChain={setContinueChain}
          parentBrewId={parentBrewId}
          onNavigate={navigate}
          coffeeData={coffeeData}
          setCoffeeData={setCoffeeFromSearch}
          selectedSize={selectedSize}
          setSelectedSize={setSelectedSize}
        />
      )}
      {view === 'recipe' && (
        <RecipeView
          key={`recipe-${selectedBagId ?? 'none'}-${parentBrewId ?? 'none'}`}
          coffeeData={coffeeData}
          bag={selectedBag}
          parentBrewId={parentBrewId}
          brewOz={selectedSize}
          grinderId={eq.grinderId}
          grinderName={eq.grinderName}
          brewerId={eq.brewerId}
          brewerName={eq.brewerName}
          tempUnit={api.tempUnit}
          apiFetch={api.apiFetch}
          onSetRoastDate={bags.setRoastDate}
          onBrewAgain={handleBrewAgain}
          onBack={handleBack}
          onStartOver={handleStartOver}
        />
      )}
      {view === 'settings' && (
        <SettingsView
          api={api}
          equipment={eq}
          theme={theme}
          setTheme={setTheme}
          onDone={() => setView(previousView)}
          onViewHistory={() => navigate('history')}
          onViewAidenProfiles={() => navigate('aidenProfiles')}
        />
      )}
      {view === 'history' && (
        <HistoryView
          apiFetch={api.apiFetch}
          onDone={() => setView('settings')}
        />
      )}
      {view === 'aidenProfiles' && (
        <AidenProfilesView
          apiFetch={api.apiFetch}
          tempUnit={api.tempUnit}
          onDone={() => setView('settings')}
        />
      )}
    </div>
  );
}
