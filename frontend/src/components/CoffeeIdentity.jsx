import styles from './CoffeeIdentity.module.css';

export function CoffeeIdentity({ coffeeData }) {
  if (!coffeeData) return null;

  const { coffee_name, roaster, roast, origin, process, variety, flavor_notes, confidence, reasoning } = coffeeData;

  const tags = [roast, origin, process, variety].filter(Boolean);

  const confidenceClass = confidence === 'high' ? styles.badgeHigh
    : confidence === 'medium' ? styles.badgeMedium
    : styles.badgeLow;

  return (
    <div class={styles.identity}>
      <div class={styles.nameRow}>
        <h3 class={styles.name}>{coffee_name}</h3>
        {confidence && <span class={`${styles.badge} ${confidenceClass}`}>{confidence}</span>}
      </div>
      {roaster && <p class={styles.roaster}>{roaster}</p>}

      {tags.length > 0 && (
        <div class={styles.tags}>
          {tags.map(tag => (
            <span class={styles.tag} key={tag}>{tag}</span>
          ))}
        </div>
      )}

      {flavor_notes && <p class={styles.notes}>{flavor_notes}</p>}
      {reasoning && <p class={styles.reasoning}>{reasoning}</p>}
    </div>
  );
}
