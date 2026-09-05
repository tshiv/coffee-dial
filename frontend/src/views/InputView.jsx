import { useState, useEffect } from 'preact/hooks';
import { Header } from '../components/Header';
import { CoffeeSearch } from '../components/CoffeeSearch';
import { CoffeeIdentity } from '../components/CoffeeIdentity';
import { SizePicker } from '../components/SizePicker';
import { BagShelf } from '../components/BagShelf';
import { ratingLabel } from '../lib/format';
import styles from './InputView.module.css';

export function InputView({
  api, equipment, bags, selectedBag, onSelectBag, continueChain, setContinueChain, parentBrewId,
  onNavigate, coffeeData, setCoffeeData, selectedSize, setSelectedSize,
}) {
  const [presets, setPresets] = useState([]);
  const [selectedPresetId, setSelectedPresetId] = useState(null);
  const [customOz, setCustomOz] = useState(12);
  const [adding, setAdding] = useState(false);
  const [prefill, setPrefill] = useState(null);

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

  const saveSearchAsBag = () => {
    setPrefill(coffeeData);
    setAdding(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const canProceed = coffeeData && selectedSize > 0;
  const last = selectedBag?.last_brew;
  const hasChain = !!(last && last.rating);
  const nextVersion = hasChain ? last.version + 1 : 1;

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

      <BagShelf
        bags={bags}
        selectedId={selectedBag?.id ?? null}
        onSelect={onSelectBag}
        adding={adding}
        setAdding={(v) => { setAdding(v); if (!v) setPrefill(null); }}
        prefill={prefill}
      />

      {!selectedBag && (
        <CoffeeSearch apiFetch={api.apiFetch} onResult={setCoffeeData} />
      )}
      <CoffeeIdentity coffeeData={coffeeData} />

      {coffeeData && !selectedBag && !adding && (
        <button class={styles.saveAsBag} onClick={saveSearchAsBag}>
          Save as a bag → track when it's ready
        </button>
      )}

      {hasChain && (
        <div class={styles.dialin}>
          <p class={styles.dialinLabel}>DIAL-IN</p>
          <p class={styles.dialinText}>
            v{last.version} was rated <strong>{ratingLabel(last.rating)}</strong>.
            {last.chain_complete
              ? ' It\'s dialed in — brewing it the same way.'
              : ` Next is v${nextVersion}: one change from v${last.version}.`}
          </p>
          <div class={styles.dialinToggle}>
            <button
              class={`${styles.toggleBtn} ${continueChain ? styles.toggleActive : ''}`}
              onClick={() => setContinueChain(true)}
            >
              {last.chain_complete ? `Brew v${nextVersion} as dialed in` : `Continue at v${nextVersion}`}
            </button>
            <button
              class={`${styles.toggleBtn} ${!continueChain ? styles.toggleActive : ''}`}
              onClick={() => setContinueChain(false)}
            >
              Start fresh at v1
            </button>
          </div>
        </div>
      )}

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
        {parentBrewId ? `Get v${nextVersion} recipe →` : 'Get my recipe →'}
      </button>
    </>
  );
}
