import styles from './SizePicker.module.css';

export function SizePicker({ presets, selectedId, customOz, onSelect, onCustom }) {
  return (
    <div>
      <p class={styles.label}>SIZE</p>
      <div class={styles.grid}>
        {presets.map(p => (
          <button
            key={p.id}
            class={`${styles.card} ${selectedId === p.id ? styles.cardSelected : ''}`}
            onClick={() => onSelect(p.id, p.oz)}
          >
            <div class={styles.cardName}>{p.name}</div>
            <div class={styles.cardOz}>{p.oz}</div>
            <div class={styles.cardUnit}>oz</div>
          </button>
        ))}
      </div>
      <div class={styles.customRow}>
        <span class={styles.customLabel}>Custom</span>
        <input
          class={styles.customInput}
          type="number"
          min="1"
          max="64"
          value={customOz}
          onInput={e => onCustom(Number(e.target.value))}
          onFocus={() => onSelect(null, customOz)}
        />
        <span class={styles.customUnit}>oz</span>
      </div>
    </div>
  );
}
