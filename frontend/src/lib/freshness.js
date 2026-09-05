// Freshness vocabulary shared by the bag shelf, the recipe screen and history.
// Phases come from the backend (engine/freshness.py); nothing is computed here.

export const PHASES = {
  awaiting_roast_date: { label: 'Needs roast date', color: 'var(--color-text-muted)' },
  resting: { label: 'Resting', color: 'var(--color-yellow)' },
  ready: { label: 'Ready', color: 'var(--color-green)' },
  tired: { label: 'Tired', color: 'var(--color-red)' },
};

export function phaseInfo(phase) {
  return PHASES[phase] || { label: phase || '—', color: 'var(--color-text-muted)' };
}

export const STORAGE_OPTIONS = [
  {
    value: 'vacuum',
    label: 'Vacuum canister',
    hint: 'Counts only if you re-pump every time you close it. Fellow says an Atmos holds its seal 3–4 days; pumped once and left a week, it behaves like an airtight canister.',
  },
  { value: 'airtight', label: 'Airtight canister', hint: 'Sealed, no vacuum. The baseline.' },
  { value: 'bag_ambient', label: 'Original bag, rolled shut', hint: 'Shortest open clock.' },
];

export const ROAST_OPTIONS = ['light', 'medium-light', 'medium', 'medium-dark', 'dark'];

// One line under a bag's name: where it is on the clock.
export function freshnessSummary(bag) {
  const f = bag.freshness || {};
  if (f.phase === 'awaiting_roast_date') return 'No roast date yet, so no window.';
  const parts = [`Day ${Math.floor(f.age_days ?? 0)} off roast`];
  if (f.ready_range_days) parts.push(`ready ${f.ready_range_days[0]}–${f.ready_range_days[1]}`);
  if (f.open_age_days != null) {
    parts.push(`open ${Math.floor(f.open_age_days)}d of ~${Math.round(f.open_limit_days)}`);
  } else {
    parts.push('sealed');
  }
  if (f.frozen) parts.push('in the freezer');
  return parts.join(' · ');
}

// The bag's identity in the shape the recommendation engine expects.
export function bagToCoffee(bag) {
  return {
    coffee_name: bag.coffee_name,
    roaster: bag.roaster || '',
    roast: bag.roast || '',
    origin: bag.origin || '',
    process: bag.process || '',
    is_decaf: !!bag.is_decaf,
    flavor_notes: bag.notes || '',
    from_bag: true,
  };
}

// A bag's open dial-in, if its last brew was rated and not yet called good.
export function openChain(bag) {
  const last = bag?.last_brew;
  if (!last || !last.rating) return null;
  return last;
}
