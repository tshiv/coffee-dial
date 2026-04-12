import { useState, useEffect } from 'preact/hooks';
import styles from './SettingsView.module.css';

export function SettingsView({ api, equipment, theme, setTheme, onDone, onViewHistory }) {
  const [settings, setSettings] = useState({});
  const [presets, setPresets] = useState([]);
  const [history, setHistory] = useState([]);
  const [newPresetName, setNewPresetName] = useState('');
  const [newPresetOz, setNewPresetOz] = useState('');

  useEffect(() => {
    api.apiFetch('/settings').then(setSettings).catch(() => {});
    api.apiFetch('/presets').then(setPresets).catch(() => {});
    api.apiFetch('/history').then(setHistory).catch(() => {});
  }, []);

  const saveSetting = (key, value) => {
    const updated = { ...settings, [key]: value };
    setSettings(updated);
    api.apiFetch('/settings', {
      method: 'POST',
      body: JSON.stringify({ [key]: value }),
    }).catch(() => {});
  };

  const addPreset = () => {
    const name = newPresetName.trim();
    const oz = parseFloat(newPresetOz);
    if (!name || !oz || oz <= 0) return;
    api.apiFetch('/presets', {
      method: 'POST',
      body: JSON.stringify({ name, oz }),
    }).then((p) => {
      setPresets((prev) => [...prev, p]);
      setNewPresetName('');
      setNewPresetOz('');
    }).catch(() => {});
  };

  const deletePreset = (id) => {
    api.apiFetch(`/presets/${id}`, { method: 'DELETE' }).then(() => {
      setPresets((prev) => prev.filter((p) => p.id !== id));
    }).catch(() => {});
  };

  const clearHistory = () => {
    api.apiFetch('/history', { method: 'DELETE' }).then(() => {
      setHistory([]);
    }).catch(() => {});
  };

  return (
    <>
      <div class={styles.header}>
        <span class={styles.headerTitle}>Settings</span>
        <button class={styles.doneBtn} onClick={onDone}>Done</button>
      </div>

      {/* Equipment */}
      <div class={styles.card}>
        <div class={styles.cardTitle}>Equipment</div>
        <div class={styles.row}>
          <span class={styles.rowLabel}>Grinder</span>
          <select
            class={styles.select}
            value={equipment.grinderId}
            onChange={(e) => equipment.selectGrinder(e.target.value)}
          >
            {equipment.equipment.grinders.map((g) => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
        </div>
        <div class={styles.row}>
          <span class={styles.rowLabel}>Brewer</span>
          <select
            class={styles.select}
            value={equipment.brewerId}
            onChange={(e) => equipment.selectBrewer(e.target.value)}
          >
            {equipment.equipment.brewers.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Volume Presets */}
      <div class={styles.card}>
        <div class={styles.cardTitle}>Volume Presets</div>
        {presets.map((p) => (
          <div class={styles.presetRow} key={p.id}>
            <span class={styles.rowLabel}>{p.name} ({p.oz} oz)</span>
            <button class={styles.presetDelete} onClick={() => deletePreset(p.id)}>×</button>
          </div>
        ))}
        <div class={styles.addRow}>
          <input
            class={`${styles.input} ${styles.addInput}`}
            placeholder="Name"
            value={newPresetName}
            onInput={(e) => setNewPresetName(e.target.value)}
          />
          <input
            class={styles.input}
            placeholder="oz"
            type="number"
            style={{ width: '60px' }}
            value={newPresetOz}
            onInput={(e) => setNewPresetOz(e.target.value)}
          />
          <button class={styles.addBtn} onClick={addPreset}>Add</button>
        </div>
      </div>

      {/* AI Provider */}
      <div class={styles.card}>
        <div class={styles.cardTitle}>AI Provider</div>
        <div class={styles.row}>
          <span class={styles.rowLabel}>Provider</span>
          <select
            class={styles.select}
            value={settings.ai_provider || 'anthropic'}
            onChange={(e) => saveSetting('ai_provider', e.target.value)}
          >
            <option value="anthropic">Anthropic</option>
            <option value="openai">OpenAI</option>
          </select>
        </div>
        <div class={styles.row}>
          <span class={styles.rowLabel}>API Key</span>
          <input
            class={styles.input}
            type="password"
            placeholder="sk-..."
            value={settings.api_key || ''}
            onChange={(e) => saveSetting('api_key', e.target.value)}
          />
        </div>
      </div>

      {/* Temperature Unit */}
      <div class={styles.card}>
        <div class={styles.cardTitle}>Temperature Unit</div>
        <div class={styles.row}>
          <span class={styles.rowLabel}>Unit</span>
          <div>
            <button
              class={`${styles.themeBtn} ${(settings.temp_unit || 'F') === 'F' ? styles.themeBtnActive : ''}`}
              onClick={() => saveSetting('temp_unit', 'F')}
            >F</button>{' '}
            <button
              class={`${styles.themeBtn} ${(settings.temp_unit || 'F') === 'C' ? styles.themeBtnActive : ''}`}
              onClick={() => saveSetting('temp_unit', 'C')}
            >C</button>
          </div>
        </div>
      </div>

      {/* Theme */}
      <div class={styles.card}>
        <div class={styles.cardTitle}>Theme</div>
        <div class={styles.row}>
          <span class={styles.rowLabel}>Appearance</span>
          <div>
            {['light', 'dark', 'system'].map((t) => (
              <button
                key={t}
                class={`${styles.themeBtn} ${theme === t ? styles.themeBtnActive : ''}`}
                onClick={() => setTheme(t)}
                style={{ marginLeft: t !== 'light' ? '4px' : '0' }}
              >{t.charAt(0).toUpperCase() + t.slice(1)}</button>
            ))}
          </div>
        </div>
      </div>

      {/* Fellow Credentials */}
      <div class={styles.card}>
        <div class={styles.cardTitle}>Fellow Credentials</div>
        <div class={styles.row}>
          <span class={styles.rowLabel}>Email</span>
          <input
            class={styles.input}
            type="email"
            placeholder="email@example.com"
            value={settings.fellow_email || ''}
            onChange={(e) => saveSetting('fellow_email', e.target.value)}
          />
        </div>
        <div class={styles.row}>
          <span class={styles.rowLabel}>Password</span>
          <input
            class={styles.input}
            type="password"
            placeholder="password"
            value={settings.fellow_password || ''}
            onChange={(e) => saveSetting('fellow_password', e.target.value)}
          />
        </div>
      </div>

      {/* Brew History */}
      <div class={styles.card}>
        <div class={styles.cardTitle}>Brew History</div>
        <div class={styles.row}>
          <span class={styles.rowLabel}>{history.length} brew{history.length !== 1 ? 's' : ''} logged</span>
          <div>
            <button class={styles.themeBtn} onClick={onViewHistory}>View</button>{' '}
            <button class={styles.dangerBtn} onClick={clearHistory}>Clear All</button>
          </div>
        </div>
      </div>

      {/* Backend Status */}
      <div class={styles.card}>
        <div class={styles.cardTitle}>Backend Status</div>
        <div class={styles.row}>
          <span class={styles.rowLabel}>Server</span>
          <span class={styles.rowValue}>
            <span class={`${styles.statusDot} ${api.serverOnline ? styles.online : styles.offline}`} />
            {api.serverOnline ? 'Online' : 'Offline'}
          </span>
        </div>
      </div>

      {/* About */}
      <div class={styles.card}>
        <div class={styles.cardTitle}>About</div>
        <div class={styles.row}>
          <span class={styles.rowLabel}>Coffee Dial</span>
          <span class={styles.rowValue}>v1.0.0</span>
        </div>
      </div>
    </>
  );
}
