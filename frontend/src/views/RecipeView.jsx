import { useState, useEffect } from 'preact/hooks';
import { useTimer } from '../hooks/useTimer';
import { RecipeCard } from '../components/RecipeCard';
import { AidenProfile } from '../components/AidenProfile';
import { SimpleDrip } from '../components/SimpleDrip';
import { PourOverSteps } from '../components/PourOverSteps';
import { BrewTimer } from '../components/BrewTimer';
import { RatingRow } from '../components/RatingRow';
import { fmtTemp, formatTime } from '../lib/format';
import styles from './RecipeView.module.css';

export function RecipeView({ coffeeData, brewOz, grinderId, grinderName, brewerId, brewerName, tempUnit, apiFetch, onBack, onStartOver }) {
  const [rec, setRec] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [communityRecipes, setCommunityRecipes] = useState([]);
  const [roasterQuery, setRoasterQuery] = useState('');
  const [roasterResults, setRoasterResults] = useState([]);
  const [roasterSearching, setRoasterSearching] = useState(false);
  const [brewLinkUrl, setBrewLinkUrl] = useState('');
  const [brewLinkStatus, setBrewLinkStatus] = useState('idle');

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

  useEffect(() => {
    apiFetch(`/community-recipes?brewer_id=${encodeURIComponent(brewerId)}`)
      .then(data => setCommunityRecipes(Array.isArray(data) ? data : []))
      .catch(() => setCommunityRecipes([]));
  }, [brewerId]);

  const steps = rec?.recipe?.steps || [];
  const timer = useTimer(steps);

  if (loading) return <div class={styles.loading}>Generating recipe...</div>;
  if (error) return <div class={styles.error}>{error}</div>;
  if (!rec) return null;

  const { recipe } = rec;
  const isManual = recipe.type === 'pour_over_steps' || recipe.type === 'aeropress_steps';
  const isAiden = recipe.type === 'aiden_profile';
  const isSimple = recipe.type === 'simple_drip';

  const useCommunityRecipe = (cr) => {
    setRec(prev => ({
      ...prev,
      recipe: {
        ...prev.recipe,
        ratio: cr.ratio,
        temp_c: cr.temp_c,
        temp_f: cr.temp_f,
        dose_g: cr.dose_g,
        water_g: cr.water_g,
        total_time_s: cr.total_time_s,
        steps: cr.steps || prev.recipe.steps,
        bloom_time_s: cr.bloom_time_s,
        bloom_ratio: cr.bloom_ratio,
        pulses: cr.pulses,
        pulse_interval_s: cr.pulse_interval_s,
        profile_name: cr.profile_name,
      },
    }));
  };

  const handleRoasterSearch = async () => {
    setRoasterSearching(true);
    try {
      const data = await apiFetch('/search-roaster-recipe', {
        method: 'POST',
        body: JSON.stringify({
          coffee_name: coffeeData.coffee_name,
          roaster: roasterQuery || coffeeData.roaster,
          brewer_id: brewerId,
        }),
      });
      setRoasterResults(Array.isArray(data) ? data : []);
    } catch {
      setRoasterResults([]);
    }
    setRoasterSearching(false);
  };

  const handleBrewLinkImport = async () => {
    setBrewLinkStatus('loading');
    try {
      const data = await apiFetch('/import-brew-link', {
        method: 'POST',
        body: JSON.stringify({ url: brewLinkUrl }),
      });
      useCommunityRecipe(data);
      setBrewLinkStatus('success');
    } catch {
      setBrewLinkStatus('error');
    }
  };

  const renderRecipeCard = (cr) => (
    <div class={styles.recipeCard} key={cr.id}>
      <div class={styles.recipeCardTitle}>{cr.title}</div>
      <div class={styles.recipeCardAuthor}>{cr.author}</div>
      <div class={styles.recipeCardParams}>
        {cr.ratio && <span>{cr.ratio}</span>}
        {(cr.temp_c || cr.temp_f) && <span>{fmtTemp(cr.temp_c, cr.temp_f, tempUnit)}</span>}
        {cr.dose_g && <span>{cr.dose_g}g</span>}
        {cr.total_time_s && <span>{formatTime(cr.total_time_s)}</span>}
      </div>
      <button class={styles.useBtn} onClick={() => useCommunityRecipe(cr)}>
        Use This Recipe
      </button>
      {isAiden && cr.profile_name && (
        <button class={styles.useBtn} style={{ marginLeft: 8 }} onClick={() => {
          useCommunityRecipe(cr);
        }}>
          Push to Aiden
        </button>
      )}
    </div>
  );

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

      {communityRecipes.length > 0 && (
        <div class={styles.communitySection}>
          <p class={styles.sectionLabel}>COMMUNITY RECIPES</p>
          {communityRecipes.map(renderRecipeCard)}
        </div>
      )}

      <div class={styles.communitySection}>
        <p class={styles.sectionLabel}>ROASTER RECIPE SEARCH</p>
        <div class={styles.searchRow}>
          <input
            class={styles.searchInput}
            value={roasterQuery}
            onInput={e => setRoasterQuery(e.target.value)}
            placeholder={coffeeData.roaster || 'Roaster name'}
          />
          <button class={styles.useBtn} onClick={handleRoasterSearch} disabled={roasterSearching}>
            {roasterSearching ? 'Searching...' : 'Search'}
          </button>
        </div>
        {roasterResults.length > 0 && roasterResults.map(renderRecipeCard)}
      </div>

      {isAiden && (
        <div class={styles.communitySection}>
          <p class={styles.sectionLabel}>IMPORT BREW.LINK PROFILE</p>
          <div class={styles.importRow}>
            <input
              class={styles.searchInput}
              value={brewLinkUrl}
              onInput={e => setBrewLinkUrl(e.target.value)}
              placeholder="https://brew.link/..."
            />
            <button class={styles.useBtn} onClick={handleBrewLinkImport} disabled={brewLinkStatus === 'loading'}>
              {brewLinkStatus === 'loading' ? 'Importing...' : 'Import'}
            </button>
          </div>
          {brewLinkStatus === 'success' && <p class={styles.importStatus} style={{ color: 'var(--color-green)' }}>Profile imported</p>}
          {brewLinkStatus === 'error' && <p class={styles.importStatus} style={{ color: 'var(--color-red)' }}>Import failed. Check the URL and try again.</p>}
        </div>
      )}

      <RatingRow brewData={brewData} apiFetch={apiFetch} />

      <button class={styles.startOverBtn} onClick={onStartOver}>
        Brew something else
      </button>
    </div>
  );
}
