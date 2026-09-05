import { useState } from 'preact/hooks';
import { STORAGE_OPTIONS, ROAST_OPTIONS } from '../lib/freshness';
import { dateInputToEpoch, epochToDateInput } from '../lib/format';
import styles from './BagForm.module.css';

// Create or edit a bag. The roast date is the field that matters: without
// it the bag gets no window, and the form says so instead of hiding it.
export function BagForm({ initial = {}, onSave, onCancel, submitLabel = 'Add bag' }) {
  const [form, setForm] = useState({
    coffee_name: initial.coffee_name || '',
    roaster: initial.roaster || '',
    roast: initial.roast || '',
    origin: initial.origin || '',
    process: initial.process || '',
    is_decaf: !!initial.is_decaf,
    storage: initial.storage || 'vacuum',
    roast_date: epochToDateInput(initial.roast_date),
    notes: initial.notes || initial.flavor_notes || '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

  const storage = STORAGE_OPTIONS.find(o => o.value === form.storage);
  const hasDate = !!dateInputToEpoch(form.roast_date);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.coffee_name.trim()) { setError('Give the bag a name.'); return; }
    setSaving(true);
    setError('');
    try {
      await onSave({
        ...form,
        coffee_name: form.coffee_name.trim(),
        roast_date: dateInputToEpoch(form.roast_date),
      });
    } catch (err) {
      setError(err.message || 'Could not save');
      setSaving(false);
    }
  };

  return (
    <form class={styles.form} onSubmit={submit}>
      <label class={styles.field}>
        <span>Coffee</span>
        <input class={styles.input} value={form.coffee_name} onInput={set('coffee_name')} placeholder="Rwanda Gasharu Honey" />
      </label>

      <div class={styles.row}>
        <label class={styles.field}>
          <span>Roaster</span>
          <input class={styles.input} value={form.roaster} onInput={set('roaster')} />
        </label>
        <label class={styles.field}>
          <span>Roast</span>
          <select class={styles.input} value={form.roast} onChange={set('roast')}>
            <option value="">unknown</option>
            {ROAST_OPTIONS.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
      </div>

      <div class={styles.row}>
        <label class={styles.field}>
          <span>Origin</span>
          <input class={styles.input} value={form.origin} onInput={set('origin')} />
        </label>
        <label class={styles.field}>
          <span>Process</span>
          <input class={styles.input} value={form.process} onInput={set('process')} placeholder="washed, natural…" />
        </label>
      </div>

      <label class={`${styles.field} ${styles.dateField} ${hasDate ? '' : styles.dateMissing}`}>
        <span>Roast date <em>from the bag</em></span>
        <input class={styles.input} type="date" value={form.roast_date} onInput={set('roast_date')} />
        {!hasDate && (
          <small class={styles.hint}>
            Without it there is no window — the bag will sit as "needs roast date" until you add one.
          </small>
        )}
      </label>

      <label class={styles.field}>
        <span>Stored in</span>
        <select class={styles.input} value={form.storage} onChange={set('storage')}>
          {STORAGE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        {storage?.hint && <small class={styles.hint}>{storage.hint}</small>}
      </label>

      <label class={styles.check}>
        <input type="checkbox" checked={form.is_decaf} onChange={set('is_decaf')} />
        <span>Decaf</span>
      </label>

      <label class={styles.field}>
        <span>Notes</span>
        <input class={styles.input} value={form.notes} onInput={set('notes')} placeholder="flavor notes, lot, anything" />
      </label>

      {error && <p class={styles.error}>{error}</p>}

      <div class={styles.actions}>
        <button type="button" class={styles.cancelBtn} onClick={onCancel}>Cancel</button>
        <button type="submit" class={styles.saveBtn} disabled={saving}>
          {saving ? 'Saving…' : hasDate ? submitLabel : `${submitLabel} without roast date`}
        </button>
      </div>
    </form>
  );
}
