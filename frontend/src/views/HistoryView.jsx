import { useState, useEffect } from 'preact/hooks';
import { PhaseChip } from '../components/FreshnessLine';
import { ratingLabel } from '../lib/format';
import styles from './HistoryView.module.css';

function formatDate(ts) {
  const d = new Date(ts);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

// Stored values are the engine's vocabulary: good | bitter | bright | flat,
// comma-joined when two were recorded.
function ratingColor(rating) {
  if (rating.includes('good')) return 'var(--color-green)';
  if (rating.includes('bitter')) return 'var(--color-red)';
  if (rating.includes('bright')) return 'var(--color-yellow)';
  if (rating.includes('flat')) return 'var(--color-accent)';
  return 'var(--color-text-muted)';
}

export function HistoryView({ apiFetch, onDone }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch('/history')
      .then((data) => {
        setEntries(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <>
      <div class={styles.header}>
        <span class={styles.headerTitle}>Brew History</span>
        <button class={styles.doneBtn} onClick={onDone}>Done</button>
      </div>

      {!loading && entries.length === 0 && (
        <div class={styles.empty}>No brews yet.</div>
      )}

      {entries.map((e) => (
        <div class={styles.entry} key={e.id}>
          <div class={styles.entryName}>
            {e.coffee_name}
            {e.version > 1 && <span class={styles.versionTag}>v{e.version}</span>}
          </div>
          <div class={styles.entryMeta}>
            {formatDate(e.timestamp)}
            {e.roaster ? ` · ${e.roaster}` : ''}
          </div>
          <div class={styles.entryDetails}>
            {e.roast && `${e.roast} roast`}
            {e.origin && ` · ${e.origin}`}
            {e.grinder_setting_display && ` · Grind ${e.grinder_setting_display}`}
            {e.brew_oz && ` · ${e.brew_oz} oz`}
            {e.dose_g && ` · ${e.dose_g}g`}
          </div>
          <div class={styles.badges}>
            {e.rating && (
              <span
                class={styles.ratingBadge}
                style={{
                  color: ratingColor(e.rating),
                  background: `color-mix(in srgb, ${ratingColor(e.rating)} 15%, transparent)`,
                }}
              >
                {ratingLabel(e.rating)}
              </span>
            )}
            {e.bag_phase && (
              <span class={styles.bagSnapshot}>
                <PhaseChip phase={e.bag_phase} />
                {e.bag_age_days != null && ` day ${Math.floor(e.bag_age_days)}`}
              </span>
            )}
          </div>
        </div>
      ))}
    </>
  );
}
