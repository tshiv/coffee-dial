import styles from './SimpleDrip.module.css';

export function SimpleDrip({ recipe }) {
  return (
    <p class={styles.instructions}>
      {recipe.note || `Add ${recipe.dose_g}g coffee, fill with ${recipe.water_g}g water, press start.`}
    </p>
  );
}
