import { useState } from 'preact/hooks';
import { fmtTemp } from '../lib/format';
import styles from './RatingRow.module.css';

const RATINGS = [
  { label: 'Too Bitter', value: 'bitter' },
  { label: 'Too Bright', value: 'bright' },
  { label: 'Flat/Weak', value: 'flat' },
  { label: 'Just Right', value: 'good' },
];

const LEVER_LABELS = {
  grind: 'Grind',
  temp: 'Temperature',
  ratio: 'Ratio',
};

export function RatingRow({ brewData, apiFetch, tempUnit, onBrewAgain }) {
  const [selected, setSelected] = useState(null);
  const [saveStatus, setSaveStatus] = useState('idle');
  const [result, setResult] = useState(null);
  const [savedBrew, setSavedBrew] = useState(null);

  const handleSave = async () => {
    if (!selected) return;
    setSaveStatus('saving');
    try {
      const brew = await apiFetch('/history', {
        method: 'POST',
        body: JSON.stringify({ ...brewData, rating: selected.value }),
      });
      // Saving and dialing in are separate steps on purpose: history is
      // recorded even if the dial-in call fails.
      setSavedBrew(brew);
      setSaveStatus('saved');
      try {
        const dialin = await apiFetch(`/brews/${brew.id}/rate`, {
          method: 'POST',
          body: JSON.stringify({ rating: selected.value }),
        });
        setResult(dialin);
      } catch {
        // History is safe; the next-brew suggestion just isn't available.
      }
    } catch {
      setSaveStatus('idle');
    }
  };

  const adjustment = result?.adjustment;
  const next = result?.next_recommendation;

  return (
    <div class={styles.section}>
      <p class={styles.sectionLabel}>HOW WAS IT?</p>
      <div class={styles.ratings}>
        {RATINGS.map(r => (
          <button
            key={r.value}
            class={`${styles.ratingBtn} ${selected?.value === r.value ? styles.ratingSelected : ''}`}
            onClick={() => { setSelected(r); setSaveStatus('idle'); setResult(null); }}
          >
            {r.label}
          </button>
        ))}
      </div>

      {selected && saveStatus !== 'saved' && (
        <button
          class={styles.saveBtn}
          onClick={handleSave}
          disabled={saveStatus === 'saving'}
        >
          {saveStatus === 'saving' ? 'Saving...' : 'Save to History'}
        </button>
      )}

      {saveStatus === 'saved' && !result && (
        <p class={styles.savedMsg}>Saved to brew history</p>
      )}

      {adjustment && (
        <div class={styles.dialin}>
          {adjustment.chain_complete ? (
            <p class={styles.dialinDone}>
              Dialed in — this one's done. {adjustment.reason}
            </p>
          ) : adjustment.lever ? (
            <>
              <p class={styles.dialinLabel}>
                NEXT BREW · CHANGE ONE THING
              </p>
              <p class={styles.dialinLever}>
                {LEVER_LABELS[adjustment.lever] || adjustment.lever}
                {next && adjustment.lever === 'grind' && (
                  <span class={styles.dialinValue}> → {next.grinder_display}</span>
                )}
                {next && adjustment.lever === 'temp' && (
                  <span class={styles.dialinValue}> → {fmtTemp(next.recipe?.temp_c, next.recipe?.temp_f, tempUnit)}</span>
                )}
                {next && adjustment.lever === 'ratio' && (
                  <span class={styles.dialinValue}> → 1:{next.ratio} ({next.dose_g}g)</span>
                )}
              </p>
              <p class={styles.dialinReason}>{adjustment.reason}</p>
              {adjustment.noted?.length > 0 && (
                <p class={styles.dialinNoted}>
                  Also noted, not changed this round: {adjustment.noted.join(', ')}.
                  One variable at a time dials in faster.
                </p>
              )}
            </>
          ) : (
            <p class={styles.dialinReason}>{adjustment.reason}</p>
          )}
          {adjustment.freshness_note && (
            <p class={styles.dialinNoted}>{adjustment.freshness_note}</p>
          )}
          {!adjustment.chain_complete && savedBrew && onBrewAgain && (
            <button class={styles.againBtn} onClick={() => onBrewAgain(savedBrew.id)}>
              {adjustment.lever
                ? `Brew v${result.next_version} with this change →`
                : `Brew v${result.next_version} again →`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
