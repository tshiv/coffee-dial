import { useState, useEffect, useCallback } from 'preact/hooks';
import { nowEpoch } from '../lib/format';

// The bag shelf's state. Every mutation goes to the server and the list is
// updated from the response, so the phase you see is always the server's.
export function useBags(apiFetch, serverOnline) {
  const [bags, setBags] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!serverOnline) return;
    setLoading(true);
    try {
      setBags(await apiFetch('/bags'));
      setError('');
    } catch (e) {
      setError(e.message || 'Could not load bags');
    } finally {
      setLoading(false);
    }
  }, [apiFetch, serverOnline]);

  useEffect(() => { load(); }, [load]);

  const replace = (bag) => setBags(prev => {
    const i = prev.findIndex(b => b.id === bag.id);
    if (i === -1) return [bag, ...prev];
    const next = prev.slice();
    next[i] = bag;
    return next;
  });

  const create = async (fields) => {
    const bag = await apiFetch('/bags', { method: 'POST', body: JSON.stringify(fields) });
    replace(bag);
    return bag;
  };

  const update = async (id, fields) => {
    const bag = await apiFetch(`/bags/${id}`, { method: 'PUT', body: JSON.stringify(fields) });
    if (bag.finished_at) {
      setBags(prev => prev.filter(b => b.id !== id));
    } else {
      // PUT returns the bag without its brew summary; keep what we had.
      setBags(prev => prev.map(b => (b.id === id ? { ...b, ...bag } : b)));
    }
    return bag;
  };

  const remove = async (id) => {
    await apiFetch(`/bags/${id}`, { method: 'DELETE' });
    setBags(prev => prev.filter(b => b.id !== id));
  };

  const rebuy = async (id, fields) => {
    const bag = await apiFetch(`/bags/${id}/rebuy`, { method: 'POST', body: JSON.stringify(fields) });
    setBags(prev => [bag, ...prev.filter(b => b.id !== id)]);
    return bag;
  };

  return {
    bags, loading, error, load,
    create, update, remove, rebuy,
    open: (id) => update(id, { opened_at: nowEpoch() }),
    freeze: (id) => update(id, { frozen_at: nowEpoch(), thawed_at: null }),
    thaw: (id) => update(id, { thawed_at: nowEpoch() }),
    finish: (id) => update(id, { finished_at: nowEpoch() }),
    setRoastDate: (id, epoch) => update(id, { roast_date: epoch }),
    setStorage: (id, storage) => update(id, { storage }),
  };
}
