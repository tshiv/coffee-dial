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
