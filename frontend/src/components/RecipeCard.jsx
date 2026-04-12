import { fmtTemp } from '../lib/format';
import styles from './RecipeCard.module.css';

export function RecipeCard({ rec, tempUnit }) {
  const { grinder_display, recipe, bias_notes } = rec;
  const rows = [
    ['Grind setting', grinder_display],
    ['Water temperature', fmtTemp(recipe.temp_c, recipe.temp_f, tempUnit)],
    ['Coffee', `${recipe.dose_g}g`],
    ['Water', `${recipe.water_g}g`],
    ['Ratio', recipe.ratio],
  ];

  const historyNotes = (bias_notes || []).filter(n => n.startsWith('History:'));

  return (
    <div>
      <div class={styles.list}>
        {rows.map(([label, value]) => (
          <div class={styles.row} key={label}>
            <span class={styles.label}>{label}</span>
            <span class={styles.value}>{value}</span>
          </div>
        ))}
      </div>
      {historyNotes.length > 0 && (
        <div class={styles.learningNote}>
          {historyNotes.map(n => <p key={n}>{n.replace('History: ', '')}</p>)}
        </div>
      )}
    </div>
  );
}
