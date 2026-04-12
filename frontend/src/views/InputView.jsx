import { useState, useEffect } from 'preact/hooks';
import { Header } from '../components/Header';
import { CoffeeSearch } from '../components/CoffeeSearch';
import { CoffeeIdentity } from '../components/CoffeeIdentity';
import { SizePicker } from '../components/SizePicker';
import styles from './InputView.module.css';

export function InputView({ api, equipment, onNavigate, coffeeData, setCoffeeData, selectedSize, setSelectedSize }) {
  const [presets, setPresets] = useState([]);
  const [selectedPresetId, setSelectedPresetId] = useState(null);
  const [customOz, setCustomOz] = useState(12);

  useEffect(() => {
    if (api.serverOnline) {
      api.apiFetch('/presets').then(setPresets).catch(() => {});
    }
  }, [api.serverOnline]);

  const handleSizeSelect = (id, oz) => {
    setSelectedPresetId(id);
    setSelectedSize(oz);
  };

  const handleCustom = (oz) => {
    setCustomOz(oz);
    setSelectedPresetId(null);
    setSelectedSize(oz);
  };

  const canProceed = coffeeData && selectedSize > 0;

  return (
    <>
      <Header
        grinderName={equipment.grinderName}
        brewerName={equipment.brewerName}
        onGearClick={() => onNavigate('settings')}
      />

      {!api.serverOnline && (
        <div class={styles.offline}>Backend server is offline. Start it to search for coffee.</div>
      )}

      <CoffeeSearch apiFetch={api.apiFetch} onResult={setCoffeeData} />
      <CoffeeIdentity coffeeData={coffeeData} />

      <div style={{ marginTop: '24px' }}>
        <SizePicker
          presets={presets}
          selectedId={selectedPresetId}
          customOz={customOz}
          onSelect={handleSizeSelect}
          onCustom={handleCustom}
        />
      </div>

      <button
        class={`${styles.cta} ${!canProceed ? styles.ctaDisabled : ''}`}
        onClick={() => canProceed && onNavigate('recipe')}
        disabled={!canProceed}
      >
        Get my recipe →
      </button>
    </>
  );
}
