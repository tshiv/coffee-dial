import { useState } from 'preact/hooks';
import { fmtTemp } from '../lib/format';
import styles from './AidenProfile.module.css';

export function AidenProfile({ recipe, tempUnit, coffeeName, apiFetch }) {
  const [profileName, setProfileName] = useState(recipe.profile_name || coffeeName || '');
  const [pushStatus, setPushStatus] = useState('idle');

  const handlePush = async () => {
    setPushStatus('loading');
    try {
      await apiFetch('/push-aiden', {
        method: 'POST',
        body: JSON.stringify({
          profile_name: profileName,
          temp_c: recipe.temp_c,
          temp_f: recipe.temp_f,
          ratio: recipe.ratio,
          bloom_time_s: recipe.bloom_time_s,
          bloom_ratio: recipe.bloom_ratio,
        }),
      });
      setPushStatus('success');
    } catch {
      setPushStatus('error');
    }
  };

  const cells = [
    ['Bloom', `${recipe.bloom_time_s}s`],
    ['Bloom Ratio', recipe.bloom_ratio],
    ['Pulses', recipe.pulses],
    ['Interval', `${recipe.pulse_interval_s}s`],
    ['Temp', fmtTemp(recipe.temp_c, recipe.temp_f, tempUnit)],
    ['Ratio', recipe.ratio],
  ];

  return (
    <div>
      <div class={styles.grid}>
        {cells.map(([label, value]) => (
          <div class={styles.cell} key={label}>
            <div class={styles.cellLabel}>{label}</div>
            <div class={styles.cellValue}>{value}</div>
          </div>
        ))}
      </div>
      <div class={styles.pushRow}>
        <input
          class={styles.profileInput}
          value={profileName}
          onInput={e => setProfileName(e.target.value)}
          placeholder="Profile name"
        />
        <button class={styles.pushBtn} onClick={handlePush} disabled={pushStatus === 'loading'}>
          {pushStatus === 'loading' ? 'Pushing...' : 'Push to Aiden'}
        </button>
      </div>
      {pushStatus === 'success' && <p class={styles.pushStatus} style={{ color: 'var(--color-green)' }}>Profile pushed successfully</p>}
      {pushStatus === 'error' && <p class={styles.pushStatus} style={{ color: 'var(--color-red)' }}>Push failed. Check Fellow credentials in settings.</p>}
    </div>
  );
}
