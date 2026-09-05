export function fmtTemp(tempC, tempF, unit) {
  return unit === 'C' ? `${tempC}\u00B0C` : `${tempF}\u00B0F`;
}

export function fmtTempValue(tempC, tempF, unit) {
  return unit === 'C' ? tempC : tempF;
}

export function cToF(c) {
  return Math.round(c * 9 / 5 + 32);
}

export function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

// Bag dates are epoch seconds; brew timestamps are epoch milliseconds.
export function nowEpoch() {
  return Math.floor(Date.now() / 1000);
}

export function epochToDateInput(sec) {
  if (!sec) return '';
  const d = new Date(sec * 1000);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// Local noon, so a date typed on the bag never lands on the previous day
// once it is turned back into a calendar date.
export function dateInputToEpoch(str) {
  if (!str) return null;
  const [y, m, d] = str.split('-').map(Number);
  if (!y || !m || !d) return null;
  return Math.floor(new Date(y, m - 1, d, 12, 0, 0).getTime() / 1000);
}

export function formatEpochDate(sec) {
  if (!sec) return '';
  return new Date(sec * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export const RATING_LABELS = {
  bitter: 'Too Bitter',
  bright: 'Too Bright',
  flat: 'Flat/Weak',
  good: 'Just Right',
};

export function ratingLabel(rating) {
  if (!rating) return '';
  return rating.split(',').map(r => RATING_LABELS[r.trim()] || r.trim()).join(' + ');
}
