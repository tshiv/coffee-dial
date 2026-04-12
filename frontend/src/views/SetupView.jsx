import { useState } from 'preact/hooks';
import styles from './SetupView.module.css';

export function SetupView({ equipment, onComplete }) {
  const [grinderId, setGrinderId] = useState(equipment.grinders[0]?.id || '');
  const [brewerId, setBrewerId] = useState(equipment.brewers[0]?.id || '');

  const handleSubmit = () => {
    if (grinderId && brewerId) {
      onComplete(grinderId, brewerId);
    }
  };

  const renderOptions = (items, type) => {
    const groups = type === 'grinder'
      ? [['electric', 'Electric'], ['manual', 'Manual']]
      : [['automatic', 'Automatic'], ['manual', 'Manual']];

    return groups.map(([key, label]) => {
      const filtered = items.filter(item => item.type === key);
      if (!filtered.length) return null;
      return (
        <optgroup label={label} key={key}>
          {filtered.map(item => (
            <option value={item.id} key={item.id}>{item.name}</option>
          ))}
        </optgroup>
      );
    });
  };

  return (
    <div class={styles.setup}>
      <div class={styles.logoBig}>
        <div class={styles.logoBigMark} />
      </div>
      <h2 class={styles.title}>Coffee Dial</h2>
      <p class={styles.subtitle}>Pick your grinder and brewer to get started.</p>

      <div class={styles.field}>
        <label class={styles.label}>Grinder</label>
        <select
          class={styles.select}
          value={grinderId}
          onChange={e => setGrinderId(e.target.value)}
        >
          {renderOptions(equipment.grinders, 'grinder')}
        </select>
      </div>

      <div class={styles.field}>
        <label class={styles.label}>Brewer</label>
        <select
          class={styles.select}
          value={brewerId}
          onChange={e => setBrewerId(e.target.value)}
        >
          {renderOptions(equipment.brewers, 'brewer')}
        </select>
      </div>

      <button class={styles.cta} onClick={handleSubmit}>Let's Brew</button>
    </div>
  );
}
