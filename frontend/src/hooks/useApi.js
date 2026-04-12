import { useState, useEffect, useCallback } from 'preact/hooks';

export function useApi() {
  const [serverOnline, setServerOnline] = useState(false);
  const [tempUnit, setTempUnit] = useState('F');

  const checkServer = useCallback(async () => {
    try {
      const r = await fetch('/api/settings', { signal: AbortSignal.timeout(3000) });
      if (r.ok) {
        setServerOnline(true);
        const s = await r.json();
        setTempUnit(s.temp_unit || 'F');
      } else {
        setServerOnline(false);
      }
    } catch {
      setServerOnline(false);
    }
  }, []);

  useEffect(() => {
    checkServer();
    const interval = setInterval(checkServer, 15000);
    return () => clearInterval(interval);
  }, [checkServer]);

  const apiFetch = useCallback(async (path, options = {}) => {
    const r = await fetch('/api' + path, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Request failed');
    return data;
  }, []);

  return { serverOnline, tempUnit, setTempUnit, apiFetch, checkServer };
}
