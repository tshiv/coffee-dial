import { useState, useEffect } from 'preact/hooks';
import { useTimer } from '../hooks/useTimer';
import { RecipeCard } from '../components/RecipeCard';
import { AidenProfile } from '../components/AidenProfile';
import { SimpleDrip } from '../components/SimpleDrip';
import { PourOverSteps } from '../components/PourOverSteps';
import { BrewTimer } from '../components/BrewTimer';
import { RatingRow } from '../components/RatingRow';
import styles from './RecipeView.module.css';

export function RecipeView({ coffeeData, brewOz, grinderId, grinderName, brewerId, brewerName, tempUnit, apiFetch, onBack, onStartOver }) {
  const [rec, setRec] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    setLoading(true);
    setError('');
    apiFetch('/recommend', {
      method: 'POST',
      body: JSON.stringify({
        coffee: coffeeData,
        grinder_id: grinderId,
        brewer_id: brewerId,
        brew_oz: brewOz,
      }),
    })
      .then(data => { setRec(data); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  const steps = rec?.recipe?.steps || [];
  const timer = useTimer(steps);

  if (loading) return <div class={styles.loading}>Generating recipe...</div>;
  if (error) return <div class={styles.error}>{error}</div>;
  if (!rec) return null;

  const { recipe } = rec;
  const isManual = recipe.type === 'pour_over_steps' || recipe.type === 'aeropress_steps';
  const isAiden = recipe.type === 'aiden_profile';
  const isSimple = recipe.type === 'simple_drip';

  const tags = [coffeeData.roast, coffeeData.origin, coffeeData.process].filter(Boolean);

  const brewData = {
    coffee_name: coffeeData.coffee_name,
    roaster: coffeeData.roaster,
    roast: coffeeData.roast,
    origin: coffeeData.origin,
    grinder_id: grinderId,
    brewer_id: brewerId,
    grind_setting: rec.grinder_display,
    brew_oz: brewOz,
    dose_g: recipe.dose_g,
    water_g: recipe.water_g,
    temp_f: recipe.temp_f,
    ratio: recipe.ratio,
  };

  return (
    <div>
      <a class={styles.backLink} onClick={onBack}>&larr; Change coffee</a>

      <h1 class={styles.coffeeName}>{coffeeData.coffee_name}</h1>
      <p class={styles.meta}>
        {[coffeeData.roaster, ...tags].filter(Boolean).join(' \u00B7 ')}
      </p>
      {coffeeData.flavor_notes && (
        <p class={styles.notes}>{coffeeData.flavor_notes}</p>
      )}
      <p class={styles.context}>
        Brewing {brewOz}oz on {grinderName} &rsaquo; {brewerName}
      </p>

      <hr class={styles.divider} />

      <RecipeCard rec={rec} tempUnit={tempUnit} />

      {isAiden && (
        <>
          <p class={styles.sectionLabel}>AIDEN PROFILE</p>
          <AidenProfile recipe={recipe} tempUnit={tempUnit} coffeeName={coffeeData.coffee_name} apiFetch={apiFetch} />
        </>
      )}

      {isManual && (
        <>
          <p class={styles.sectionLabel}>BREW STEPS</p>
          <PourOverSteps recipe={recipe} activeStep={timer.activeStep} />
          <BrewTimer
            elapsed={timer.elapsed}
            running={timer.running}
            onStart={timer.start}
            onPause={timer.pause}
            onReset={timer.reset}
          />
        </>
      )}

      {isSimple && (
        <>
          <p class={styles.sectionLabel}>INSTRUCTIONS</p>
          <SimpleDrip recipe={recipe} />
        </>
      )}

      <RatingRow brewData={brewData} apiFetch={apiFetch} />

      <button class={styles.startOverBtn} onClick={onStartOver}>
        Brew something else
      </button>
    </div>
  );
}
