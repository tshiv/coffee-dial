import { formatTime } from '../lib/format';
import styles from './PourOverSteps.module.css';

export function PourOverSteps({ recipe, activeStep }) {
  const steps = recipe.steps || [];
  let cumulative = 0;

  return (
    <div>
      <div class={styles.timeline}>
        {steps.map((step, i) => {
          const startTime = cumulative;
          const endTime = cumulative + (step.duration_s || 0);
          cumulative = endTime;
          const isActive = i === activeStep;

          return (
            <div class={styles.step} key={i}>
              <div class={`${styles.dot} ${isActive ? styles.dotActive : ''}`} />
              <div class={isActive ? styles.stepActionActive : styles.stepAction}>
                {step.action}
              </div>
              <div class={styles.stepNote}>{step.note}</div>
              <div class={styles.stepTime}>
                {formatTime(startTime)} – {formatTime(endTime)}
              </div>
            </div>
          );
        })}
      </div>
      {recipe.target_total_time_s && (
        <p class={styles.totalTime}>
          Target total time: {formatTime(recipe.target_total_time_s)}
        </p>
      )}
    </div>
  );
}
