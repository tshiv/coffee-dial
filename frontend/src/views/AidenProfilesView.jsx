import { useState, useEffect } from 'preact/hooks';
import styles from './AidenProfilesView.module.css';

function formatDate(epochSeconds) {
  if (!epochSeconds) return null;
  return new Date(epochSeconds * 1000).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

function formatIso(iso) {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

function tempDisplay(c, unit) {
  if (c === null || c === undefined) return '—';
  if (unit === 'F') return `${Math.round(c * 9 / 5 + 32)}°F`;
  return `${Math.round(c * 10) / 10}°C`;
}

export function AidenProfilesView({ apiFetch, tempUnit, onDone }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  const load = () => {
    setLoading(true);
    setError('');
    apiFetch('/aiden-profiles')
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(e.message || 'Could not reach the brewer'); setLoading(false); });
  };

  useEffect(load, []);

  const profiles = data?.profiles || [];
  const folders = [...new Set(profiles.map(p => p.folder))];
  const usedCount = profiles.filter(p => p.last_used).length;

  return (
    <>
      <div class={styles.header}>
        <span class={styles.headerTitle}>Aiden Profiles</span>
        <button class={styles.doneBtn} onClick={onDone}>Done</button>
      </div>

      {loading && <div class={styles.empty}>Reading the brewer…</div>}

      {error && (
        <div class={styles.error}>
          {error}
          <button class={styles.retryBtn} onClick={load}>Retry</button>
        </div>
      )}

      {data && (
        <>
          <div class={styles.summary}>
            <div class={styles.summaryRow}>
              <span>{data.brewer}</span>
              <span>{data.count} profiles</span>
            </div>
            {data.device_totals?.total_brewing_cycles != null && (
              <div class={styles.summaryNote}>
                {data.device_totals.total_brewing_cycles.toLocaleString()} brews on this
                machine all-time. Fellow does not track brews per profile, so there is no
                per-recipe count to show.
              </div>
            )}
            <div class={styles.summaryNote}>
              {usedCount} of {data.count} profiles have ever recorded a last-used date.
            </div>
          </div>

          {folders.map(folder => (
            <div class={styles.folder} key={folder}>
              <p class={styles.folderLabel}>{folder}</p>

              {profiles.filter(p => p.folder === folder).map(p => (
                <div class={styles.profile} key={p.id}>
                  <button
                    class={styles.profileHead}
                    onClick={() => setExpanded(expanded === p.id ? null : p.id)}
                  >
                    <span class={styles.profileTitle}>
                      {p.title}
                      {p.is_cold_brew && <span class={styles.tag}>cold brew</span>}
                    </span>
                    <span class={styles.profileMeta}>
                      {p.last_used
                        ? `last used ${formatDate(p.last_used)}`
                        : 'never used'}
                    </span>
                  </button>

                  <div class={styles.profileQuick}>
                    1:{p.ratio} · {tempDisplay(p.temp_c, tempUnit)}
                    {p.temp_is_derived && <span class={styles.derived} title="Fellow left this profile's overall temperature empty; taken from its pulse temperatures">derived</span>}
                    {p.pulses > 1 && ` · ${p.pulses} pulses`}
                  </div>

                  {expanded === p.id && (
                    <dl class={styles.details}>
                      <dt>Profile ID</dt><dd>{p.id}</dd>
                      <dt>Ratio</dt><dd>1:{p.ratio}</dd>
                      <dt>Temperature</dt>
                      <dd>
                        {tempDisplay(p.temp_c, tempUnit)}
                        {p.temp_is_derived && ' (derived from pulse temps)'}
                      </dd>
                      <dt>Bloom</dt>
                      <dd>
                        {p.bloom_enabled
                          ? `${p.bloom_duration_s}s at 1:${p.bloom_ratio}, ${tempDisplay(p.bloom_temp_c, tempUnit)}`
                          : 'off'}
                      </dd>
                      <dt>Pulses</dt>
                      <dd>
                        {p.pulses}
                        {p.pulse_interval_s ? ` every ${p.pulse_interval_s}s` : ''}
                        {p.pulse_temps_c?.length > 0 &&
                          ` — ${p.pulse_temps_c.map(t => tempDisplay(t, tempUnit)).join(', ')}`}
                      </dd>
                      <dt>Last used</dt>
                      <dd>{formatDate(p.last_used) || 'never'}</dd>
                      {p.added_at && (<><dt>Added</dt><dd>{formatIso(p.added_at)}</dd></>)}
                      {p.updated_at && (<><dt>Updated</dt><dd>{formatIso(p.updated_at)}</dd></>)}
                    </dl>
                  )}
                </div>
              ))}
            </div>
          ))}
        </>
      )}
    </>
  );
}
