import { useState } from 'preact/hooks';
import styles from './RatingRow.module.css';

const RATINGS = [
  { label: 'Too Bitter', value: 'bitter' },
  { label: 'Too Bright', value: 'bright' },
  { label: 'Flat/Weak', value: 'flat' },
  { label: 'Just Right', value: 'good' },
];

export function RatingRow({ brewData, apiFetch }) {
  const [selected, setSelected] = useState(null);
  const [saveStatus, setSaveStatus] = useState('idle');

  const handleSave = async () => {
    if (!selected) return;
    setSaveStatus('saving');
    try {
      await apiFetch('/history', {
        method: 'POST',
        body: JSON.stringify({ ...brewData, rating: selected.value }),
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
            key={r.value}
            class={`${styles.ratingBtn} ${selected?.value === r.value ? styles.ratingSelected : ''}`}
            onClick={() => { setSelected(r); setSaveStatus('idle'); }}
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
      {saveStatus === 'saved' && (
        <p class={styles.savedMsg}>Saved to brew history</p>
      )}
    </div>
  );
}
