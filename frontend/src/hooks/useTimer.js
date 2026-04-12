import { useState, useEffect, useRef, useCallback } from 'preact/hooks';

export function useTimer(steps) {
  const [elapsed, setElapsed] = useState(0);
  const [running, setRunning] = useState(false);
  const intervalRef = useRef(null);
  const prevStepRef = useRef(-1);

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => {
        setElapsed(e => e + 1);
      }, 1000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
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
    prevStepRef.current = -1;
  }, []);

  return { elapsed, running, activeStep, start, pause, reset };
}
