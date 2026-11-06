import { useState, useEffect, useRef, useCallback } from 'preact/hooks';

export function useTimer(steps) {
  const [elapsed, setElapsed] = useState(0);
  const [running, setRunning] = useState(false);
  const prevStepRef = useRef(-1);
  // Elapsed time is measured from the wall clock, not counted in ticks:
  // browsers throttle timers in a background tab or with the phone locked,
  // and a tick counter falls behind the real brew.
  const startedAtRef = useRef(null);   // ms timestamp of the current run
  const accumulatedRef = useRef(0);    // seconds from earlier runs, before a pause

  useEffect(() => {
    if (!running) return undefined;
    startedAtRef.current = Date.now();
    const sync = () => {
      const runS = (Date.now() - startedAtRef.current) / 1000;
      setElapsed(Math.floor(accumulatedRef.current + runS));
    };
    const id = setInterval(sync, 250);
    document.addEventListener('visibilitychange', sync);
    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', sync);
      accumulatedRef.current += (Date.now() - startedAtRef.current) / 1000;
      startedAtRef.current = null;
    };
  }, [running]);

  let activeStep = -1;
  if (steps && steps.length && elapsed > 0) {
    let cumulative = 0;
    for (let i = 0; i < steps.length; i++) {
      const dur = steps[i].duration_s || 0;
      if (elapsed <= cumulative + dur || i === steps.length - 1) {
        activeStep = i;
        break;
      }
      cumulative += dur;
    }
  }

  useEffect(() => {
    if (activeStep !== prevStepRef.current && activeStep >= 0 && running) {
      prevStepRef.current = activeStep;
      if (navigator.vibrate) {
        navigator.vibrate(200);
      }
    }
  }, [activeStep, running]);

  const start = useCallback(() => setRunning(true), []);
  const pause = useCallback(() => setRunning(false), []);
  const reset = useCallback(() => {
    setRunning(false);
    setElapsed(0);
    accumulatedRef.current = 0;
    // A running timer's cleanup still adds "now minus start" when it stops;
    // move the start to now so that adds nothing.
    if (startedAtRef.current !== null) startedAtRef.current = Date.now();
    prevStepRef.current = -1;
  }, []);

  return { elapsed, running, activeStep, start, pause, reset };
}
