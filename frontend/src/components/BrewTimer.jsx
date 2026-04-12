import { formatTime } from '../lib/format';
import styles from './BrewTimer.module.css';

export function BrewTimer({ elapsed, running, onStart, onPause, onReset }) {
  return (
    <div class={styles.timer}>
      <div class={styles.display}>{formatTime(elapsed)}</div>
      <div class={styles.buttons}>
        {running ? (
          <button class={styles.startBtn} onClick={onPause}>Pause</button>
        ) : (
          <button class={styles.startBtn} onClick={onStart}>
            {elapsed > 0 ? 'Resume' : 'Start'}
          </button>
        )}
        <button class={styles.resetBtn} onClick={onReset}>Reset</button>
      </div>
    </div>
  );
}
