import { useState, useEffect } from 'preact/hooks';
import styles from './HistoryView.module.css';

function formatDate(ts) {
  const d = new Date(ts);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function ratingColor(rating) {
  if (rating === 'Just Right') return 'var(--color-green)';
  if (rating === 'Too Strong') return 'var(--color-red)';
  if (rating === 'Too Weak') return 'var(--color-accent)';
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
          <div class={styles.entryName}>{e.coffee_name}</div>
          <div class={styles.entryMeta}>
            {formatDate(e.timestamp)}
            {e.roaster ? ` · ${e.roaster}` : ''}
          </div>
          <div class={styles.entryDetails}>
            {e.roast && `${e.roast} roast`}
            {e.origin && ` · ${e.origin}`}
            {e.grind_setting && ` · Grind ${e.grind_setting}`}
            {e.brew_oz && ` · ${e.brew_oz} oz`}
            {e.dose_g && ` · ${e.dose_g}g`}
          </div>
          {e.rating && (
            <span
              class={styles.ratingBadge}
              style={{
                color: ratingColor(e.rating),
                background: `color-mix(in srgb, ${ratingColor(e.rating)} 15%, transparent)`,
              }}
            >
              {e.rating}
            </span>
          )}
        </div>
      ))}
    </>
  );
}
