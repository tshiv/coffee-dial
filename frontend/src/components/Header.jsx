import styles from './Header.module.css';

export function Header({ grinderName, brewerName, onGearClick }) {
  const equipmentText = [grinderName, brewerName].filter(Boolean).join(' \u00B7 ');

  return (
    <header class={styles.header}>
      <div class={styles.left}>
        <div class={styles.logo}>
          <div class={styles.logoMark} />
        </div>
        <span class={styles.title}>Coffee Dial</span>
      </div>
      <div class={styles.right}>
        {equipmentText && <span class={styles.equipment}>{equipmentText}</span>}
        <button class={styles.gearBtn} onClick={onGearClick} title="Settings">
          &#9881;
        </button>
      </div>
    </header>
  );
}
