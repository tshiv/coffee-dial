import { useState } from 'preact/hooks';
import { phaseInfo, freshnessSummary } from '../lib/freshness';
import { dateInputToEpoch } from '../lib/format';
import styles from './FreshnessLine.module.css';

export function PhaseChip({ phase }) {
  const info = phaseInfo(phase);
  return (
    <span
      class={styles.chip}
      style={{ color: info.color, background: `color-mix(in srgb, ${info.color} 15%, transparent)` }}
    >
      {info.label}
    </span>
  );
}

// The bag's freshness read, on the recipe screen. A bag with no roast date
// gets a prompt to enter one — never a made-up window.
export function FreshnessLine({ bag, onSetRoastDate }) {
  const [date, setDate] = useState('');
  const [saving, setSaving] = useState(false);
  if (!bag) return null;
  const f = bag.freshness || {};
  const awaiting = f.phase === 'awaiting_roast_date';
  const warn = f.phase === 'tired' || f.phase === 'resting';

  const save = async () => {
    const epoch = dateInputToEpoch(date);
    if (!epoch) return;
    setSaving(true);
    try { await onSetRoastDate(bag.id, epoch); } finally { setSaving(false); }
  };

  return (
    <div class={`${styles.line} ${warn ? styles.warn : ''}`}>
      <div class={styles.head}>
        <PhaseChip phase={f.phase} />
        <span class={styles.summary}>{freshnessSummary(bag)}</span>
      </div>
      <p class={styles.message}>{f.message}</p>
      {awaiting && onSetRoastDate && (
        <div class={styles.dateRow}>
          <input class={styles.dateInput} type="date" value={date} onInput={e => setDate(e.target.value)} />
          <button class={styles.dateBtn} onClick={save} disabled={saving || !date}>
            {saving ? 'Saving…' : 'Set roast date'}
          </button>
        </div>
      )}
    </div>
  );
}
