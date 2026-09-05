import { useState } from 'preact/hooks';
import { BagForm } from './BagForm';
import { PhaseChip } from './FreshnessLine';
import { STORAGE_OPTIONS, freshnessSummary } from '../lib/freshness';
import { dateInputToEpoch, formatEpochDate, ratingLabel } from '../lib/format';
import styles from './BagShelf.module.css';

// The bags you own, with where each one is on its clock. Tap one to brew
// from it; expand it to move it along (open, freeze, thaw, finish, rebuy).
export function BagShelf({ bags, selectedId, onSelect, adding, setAdding, prefill }) {
  const [expanded, setExpanded] = useState(null);

  return (
    <div class={styles.shelf}>
      <div class={styles.labelRow}>
        <span class={styles.sectionLabel}>YOUR BAGS</span>
        {!adding && (
          <button class={styles.addBtn} onClick={() => setAdding(true)}>+ Add bag</button>
        )}
      </div>

      {adding && (
        <BagForm
          initial={prefill || {}}
          onSave={async (fields) => {
            const bag = await bags.create(fields);
            setAdding(false);
            onSelect(bag);
          }}
          onCancel={() => setAdding(false)}
        />
      )}

      {bags.error && <p class={styles.error}>{bags.error}</p>}

      {!adding && !bags.loading && bags.bags.length === 0 && (
        <p class={styles.empty}>
          No bags yet. Add the one you're brewing from and you'll see when it's ready.
        </p>
      )}

      {bags.bags.map(bag => (
        <BagRow
          key={bag.id}
          bag={bag}
          bags={bags}
          selected={bag.id === selectedId}
          expanded={expanded === bag.id}
          onToggleExpand={() => setExpanded(expanded === bag.id ? null : bag.id)}
          onSelect={() => onSelect(bag.id === selectedId ? null : bag)}
        />
      ))}
    </div>
  );
}

function BagRow({ bag, bags, selected, expanded, onToggleExpand, onSelect }) {
  const [busy, setBusy] = useState('');
  const [date, setDate] = useState('');
  const [rebuying, setRebuying] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState('');
  const f = bag.freshness || {};
  const last = bag.last_brew;

  const run = (name, fn) => async () => {
    setBusy(name);
    setError('');
    try { await fn(); } catch (e) { setError(e.message || 'Failed'); } finally { setBusy(''); }
  };

  const saveDate = run('date', async () => {
    const epoch = dateInputToEpoch(date);
    if (!epoch) return;
    await bags.setRoastDate(bag.id, epoch);
    setDate('');
  });

  const doRebuy = run('rebuy', async () => {
    await bags.rebuy(bag.id, { roast_date: dateInputToEpoch(date) });
    setRebuying(false);
    setDate('');
  });

  const meta = [bag.roaster, bag.roast, bag.process, bag.is_decaf ? 'decaf' : null].filter(Boolean).join(' · ');

  return (
    <div class={`${styles.bag} ${selected ? styles.bagSelected : ''}`}>
      <div class={styles.bagHead}>
        <button class={styles.bagMain} onClick={onSelect}>
          <span class={styles.bagName}>
            {bag.coffee_name}
            {selected && <span class={styles.selectedTag}>brewing this</span>}
          </span>
          {meta && <span class={styles.bagMeta}>{meta}</span>}
          <span class={styles.bagSummary}>
            <PhaseChip phase={f.phase} />
            <span>{freshnessSummary(bag)}</span>
          </span>
          {last && (
            <span class={styles.bagLast}>
              v{last.version} {last.rating ? `rated ${ratingLabel(last.rating)}` : 'not rated yet'}
              {last.chain_complete ? ' · dialed in' : ''}
              {bag.brew_count > 1 ? ` · ${bag.brew_count} brews` : ''}
            </span>
          )}
        </button>
        <button class={styles.expandBtn} onClick={onToggleExpand} title="Bag actions">
          {expanded ? '−' : '⋯'}
        </button>
      </div>

      {f.phase === 'awaiting_roast_date' && (
        <div class={styles.dateRow}>
          <input class={styles.dateInput} type="date" value={date} onInput={e => setDate(e.target.value)} />
          <button class={styles.smallBtn} onClick={saveDate} disabled={busy === 'date' || !date}>
            Set roast date
          </button>
        </div>
      )}

      {expanded && (
        <div class={styles.actions}>
          <div class={styles.actionRow}>
            {!bag.opened_at && (
              <button class={styles.smallBtn} onClick={run('open', () => bags.open(bag.id))} disabled={!!busy}>Opened it</button>
            )}
            {!f.frozen ? (
              <button class={styles.smallBtn} onClick={run('freeze', () => bags.freeze(bag.id))} disabled={!!busy}>Froze it</button>
            ) : (
              <button class={styles.smallBtn} onClick={run('thaw', () => bags.thaw(bag.id))} disabled={!!busy}>Thawed it</button>
            )}
            <button class={styles.smallBtn} onClick={run('finish', () => bags.finish(bag.id))} disabled={!!busy}>Finished it</button>
            <button class={styles.smallBtn} onClick={() => { setRebuying(r => !r); setDate(''); }} disabled={!!busy}>Bought it again</button>
          </div>

          {rebuying && (
            <div class={styles.dateRow}>
              <input class={styles.dateInput} type="date" value={date} onInput={e => setDate(e.target.value)} />
              <button class={styles.smallBtn} onClick={doRebuy} disabled={busy === 'rebuy'}>
                {date ? 'Start new bag' : 'Start new bag, date later'}
              </button>
            </div>
          )}

          <div class={styles.detailRow}>
            <span class={styles.detailLabel}>Stored in</span>
            <select
              class={styles.select}
              value={bag.storage || 'vacuum'}
              onChange={run('storage', (e) => bags.setStorage(bag.id, e.target.value))}
              disabled={!!busy}
            >
              {STORAGE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <p class={styles.storageHint}>
            {STORAGE_OPTIONS.find(o => o.value === (bag.storage || 'vacuum'))?.hint}
          </p>

          <dl class={styles.details}>
            <dt>Roasted</dt><dd>{formatEpochDate(bag.roast_date) || 'unknown'}</dd>
            <dt>Opened</dt><dd>{formatEpochDate(bag.opened_at) || 'still sealed'}</dd>
            {bag.frozen_at && (<><dt>Frozen</dt><dd>{formatEpochDate(bag.frozen_at)}{bag.thawed_at ? ` → thawed ${formatEpochDate(bag.thawed_at)}` : ''}</dd></>)}
            {f.tired_day != null && (<><dt>Tired by</dt><dd>day {Math.round(f.tired_day)} sealed{f.open_limit_days != null ? `, ${Math.round(f.open_limit_days)} days open` : ''}</dd></>)}
          </dl>

          <div class={styles.actionRow}>
            {!confirmDelete ? (
              <button class={styles.dangerBtn} onClick={() => setConfirmDelete(true)}>Delete bag</button>
            ) : (
              <>
                <span class={styles.confirmText}>Delete this bag? Brews logged from it keep their freshness snapshot.</span>
                <button class={styles.dangerBtn} onClick={run('delete', () => bags.remove(bag.id))} disabled={!!busy}>Yes, delete</button>
                <button class={styles.smallBtn} onClick={() => setConfirmDelete(false)}>Keep</button>
              </>
            )}
          </div>
          {error && <p class={styles.error}>{error}</p>}
        </div>
      )}
    </div>
  );
}
