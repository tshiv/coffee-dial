import { useState, useEffect, useCallback } from 'preact/hooks';

export function useEquipment(apiFetch, serverOnline) {
  const [equipment, setEquipment] = useState({ grinders: [], brewers: [] });
  const [grinderId, setGrinderId] = useState(() => localStorage.getItem('cd_grinder') || '');
  const [brewerId, setBrewerId] = useState(() => localStorage.getItem('cd_brewer') || '');
  const [setupComplete, setSetupComplete] = useState(() => localStorage.getItem('cd_setup_complete') === '1');

  const loadEquipment = useCallback(async () => {
    if (!serverOnline) return;
    try {
      const data = await apiFetch('/equipment');
      setEquipment(data);
    } catch {
      // Server offline or error
    }
  }, [apiFetch, serverOnline]);

  useEffect(() => { loadEquipment(); }, [loadEquipment]);

  const selectGrinder = (id) => {
    setGrinderId(id);
    localStorage.setItem('cd_grinder', id);
  };

  const selectBrewer = (id) => {
    setBrewerId(id);
    localStorage.setItem('cd_brewer', id);
  };

  const completeSetup = (gId, bId) => {
    selectGrinder(gId);
    selectBrewer(bId);
    localStorage.setItem('cd_setup_complete', '1');
    setSetupComplete(true);
  };

  const grinderName = equipment.grinders.find(g => g.id === grinderId)?.name || '';
  const brewerName = equipment.brewers.find(b => b.id === brewerId)?.name || '';

  return {
    equipment,
    grinderId, brewerId,
    grinderName, brewerName,
    selectGrinder, selectBrewer,
    setupComplete, completeSetup,
    loadEquipment,
  };
}
