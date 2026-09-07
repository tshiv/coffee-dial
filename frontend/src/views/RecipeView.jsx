import { useState, useEffect } from 'preact/hooks';
import { useTimer } from '../hooks/useTimer';
import { RecipeCard } from '../components/RecipeCard';
import { AidenProfile } from '../components/AidenProfile';
import { SimpleDrip } from '../components/SimpleDrip';
import { PourOverSteps } from '../components/PourOverSteps';
import { BrewTimer } from '../components/BrewTimer';
import { RatingRow } from '../components/RatingRow';
import { FreshnessLine } from '../components/FreshnessLine';
import { fmtTemp, formatTime } from '../lib/format';
import styles from './RecipeView.module.css';

const LEVER_LABELS = { grind: 'grind', temp: 'temperature', ratio: 'ratio' };

const CONFIDENCE_LABEL = {
  high: 'High confidence · found the published recipe',
  medium: 'Medium · adapted from what was found',
  low: 'Low · nothing specific found, best guess',
};
const CONFIDENCE_STYLE = {
  high: styles.badgeHigh,
  medium: styles.badgeMedium,
  low: styles.badgeLow,
};

function formatLookupDate(epochSec) {
  return new Date(epochSec * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function RecipeView({
  coffeeData, bag, parentBrewId, brewOz, grinderId, grinderName, brewerId, brewerName,
  tempUnit, apiFetch, onSetRoastDate, onBrewAgain, onBack, onStartOver,
}) {
  const [rec, setRec] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [communityRecipes, setCommunityRecipes] = useState([]);
  const [roasterQuery, setRoasterQuery] = useState('');
  const [roasterResults, setRoasterResults] = useState([]);
  const [roasterSearching, setRoasterSearching] = useState(false);
  const [brewLinkUrl, setBrewLinkUrl] = useState('');
  const [brewLinkStatus, setBrewLinkStatus] = useState('idle');
  // The roaster's own recipe is looked up as soon as the view opens. It is
  // the first thing shown, ahead of the computed estimate.
  const [roasterRecipe, setRoasterRecipe] = useState(null);
  const [roasterStatus, setRoasterStatus] = useState(coffeeData.roaster ? 'loading' : 'no_roaster');
  const [roasterError, setRoasterError] = useState('');

  useEffect(() => {
    setLoading(true);
    setError('');
    apiFetch('/recommend', {
      method: 'POST',
      body: JSON.stringify({
        coffee_data: coffeeData,
        grinder_id: grinderId,
        brewer_id: brewerId,
        oz: brewOz,
        parent_brew_id: parentBrewId || undefined,
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

  const lookupRoasterRecipe = async (refresh = false) => {
    if (!coffeeData.roaster) return;
    setRoasterStatus('loading');
    setRoasterError('');
    try {
      const data = await apiFetch('/search-roaster-recipe', {
        method: 'POST',
        body: JSON.stringify({
          roaster: coffeeData.roaster,
          coffee_name: coffeeData.coffee_name,
          brewer_id: brewerId,
          refresh,
        }),
      });
      setRoasterRecipe(data);
      setRoasterStatus('done');
    } catch (err) {
      setRoasterError(err.message || 'Search failed');
      setRoasterStatus('error');
    }
  };

  useEffect(() => { lookupRoasterRecipe(false); }, [brewerId]);

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

  // How much to trust a card. Searched recipes carry the model's confidence
  // and the page it came from; bundled community recipes are curated and
  // always link their source.
  const renderProvenance = (cr) => {
    const conf = cr.confidence;
    const recall = cr.source_kind === 'model_recall';
    return (
      <div class={styles.badgeRow}>
        {conf && (
          <span class={`${styles.badge} ${CONFIDENCE_STYLE[conf] || styles.badgeNeutral}`} title={cr.confidence_reason || ''}>
            {CONFIDENCE_LABEL[conf] || conf}
          </span>
        )}
        {!conf && <span class={`${styles.badge} ${styles.badgeNeutral}`}>Community</span>}
        {recall && <span class={`${styles.badge} ${styles.badgeLow}`}>From memory, not searched</span>}
        {cr.source_url && (
          <a class={styles.sourceLink} href={cr.source_url} target="_blank" rel="noopener">
            Source{cr.source_url_unverified ? ' (unopened)' : ''} &#8599;
          </a>
        )}
        {cr.cached_at && <span class={styles.badgeMuted}>looked up {formatLookupDate(cr.cached_at)}</span>}
      </div>
    );
  };

  const renderRecipeCard = (cr) => (
    <div class={styles.recipeCard} key={cr.id}>
      <div class={styles.recipeCardTitle}>{cr.title}</div>
      <div class={styles.recipeCardAuthor}>{cr.author}</div>
      {renderProvenance(cr)}
      {cr.confidence_reason && <p class={styles.confidenceReason}>{cr.confidence_reason}</p>}
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

  // Field names match the brews table — anything else is silently dropped
  // by the server.
  const brewData = {
    coffee_name: coffeeData.coffee_name,
    roaster: coffeeData.roaster,
    roast: coffeeData.roast,
    origin: coffeeData.origin,
    process: coffeeData.process,
    grinder_id: grinderId,
    brewer_id: brewerId,
    grind: rec.grinder_setting,
    grinder_setting_display: rec.grinder_display,
    target_microns: rec.target_microns,
    brew_oz: brewOz,
    dose_g: recipe.dose_g,
    water_g: recipe.water_g,
    temp_c: recipe.temp_c,
    ratio: recipe.ratio,
    recipe_json: JSON.stringify(recipe),
    bag_id: bag?.id ?? null,
    parent_brew_id: parentBrewId ?? null,
    version: rec.version ?? 1,
  };

  const version = rec.version ?? 1;
  const adjustment = rec.adjustment;

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
        {version > 1 && ` · v${version}`}
      </p>

      {version > 1 && (
        <div class={styles.versionBanner}>
          <span class={styles.versionTag}>v{version}</span>
          <span class={styles.versionText}>
            {adjustment?.lever
              ? <>One change from v{version - 1}: <strong>{LEVER_LABELS[adjustment.lever] || adjustment.lever}</strong>. {adjustment.reason}</>
              : <>Same recipe as v{version - 1}. {adjustment?.reason || ''}</>}
            {adjustment?.grind_used && (
              <> You ground v{version - 1} at <strong>{adjustment.grind_used.setting}</strong> instead
              of {adjustment.grind_used.recommended_display || adjustment.grind_used.recommended}, so
              this recipe starts from there.</>
            )}
          </span>
        </div>
      )}

      <FreshnessLine bag={bag} onSetRoastDate={onSetRoastDate} />

      <div class={styles.communitySection}>
        <p class={styles.sectionLabel}>FROM THE ROASTER</p>
        {roasterStatus === 'no_roaster' && (
          <p class={styles.provenance}>
            No roaster on this coffee. Add one to the bag and Coffee Dial will look up their published recipe first.
          </p>
        )}
        {roasterStatus === 'loading' && (
          <p class={styles.provenance}>Searching {coffeeData.roaster}&rsquo;s brew guides for {coffeeData.coffee_name}...</p>
        )}
        {roasterStatus === 'error' && (
          <p class={styles.provenance} style={{ color: 'var(--color-red)' }}>
            Could not search {coffeeData.roaster}: {roasterError}
          </p>
        )}
        {roasterStatus === 'done' && roasterRecipe && renderRecipeCard(roasterRecipe)}
        {roasterStatus !== 'no_roaster' && roasterStatus !== 'loading' && (
          <button class={styles.refreshBtn} onClick={() => lookupRoasterRecipe(true)}>Search again</button>
        )}
      </div>

      {communityRecipes.length > 0 && (
        <div class={styles.communitySection}>
          <p class={styles.sectionLabel}>COMMUNITY RECIPES</p>
          {communityRecipes.map(renderRecipeCard)}
        </div>
      )}

      <hr class={styles.divider} />

      <p class={styles.sectionLabel}>COFFEE DIAL&rsquo;S ESTIMATE</p>
      <p class={styles.provenance}>
        Computed from roast, origin and process tables plus your dial-in history. Not a published recipe.
      </p>
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

      <div class={styles.communitySection}>
        <p class={styles.sectionLabel}>SEARCH ANOTHER ROASTER</p>
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

      <RatingRow brewData={brewData} apiFetch={apiFetch} tempUnit={tempUnit} onBrewAgain={onBrewAgain} />

      <button class={styles.startOverBtn} onClick={onStartOver}>
        Brew something else
      </button>
    </div>
  );
}
