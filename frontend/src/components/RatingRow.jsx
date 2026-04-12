import { useState } from 'preact/hooks';
import styles from './RatingRow.module.css';

const RATINGS = ['Too Bitter', 'Too Bright', 'Flat/Weak', 'Just Right'];

export function RatingRow({ brewData, apiFetch }) {
  const [selected, setSelected] = useState(null);
  const [saveStatus, setSaveStatus] = useState('idle');

  const handleSave = async () => {
    if (!selected) return;
    setSaveStatus('saving');
    try {
      await apiFetch('/history', {
        method: 'POST',
        body: JSON.stringify({ ...brewData, rating: selected }),
      });
      setSaveStatus('saved');
    } catch {
      setSaveStatus('idle');
    }
  };

  return (
    <div class={styles.section}>
      <p class={styles.sectionLabel}>HOW WAS IT?</p>
      <div class={styles.ratings}>
        {RATINGS.map(r => (
          <button
            key={r}
            class={`${styles.ratingBtn} ${selected === r ? styles.ratingSelected : ''}`}
            onClick={() => { setSelected(r); setSaveStatus('idle'); }}
          >
            {r}
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
      {saveStatus === 'saved' && (
        <p class={styles.savedMsg}>Saved to brew history</p>
      )}
    </div>
  );
}
