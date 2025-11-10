"use client";

import { useEffect, useState } from "react";
import { ControlPanel } from "@/components/ControlPanel";
import { MapView } from "@/components/MapView";
import {
  fetchPresets,
  pauseRun,
  resetRun,
  resumeRun,
  setSpeed,
  startRun,
  stepRun,
} from "@/lib/api";
import type { RunStartPayload, SimState } from "@/lib/types";
import { connectStateStream } from "@/lib/websocket";

export default function LivePage() {
  const [presets, setPresets] = useState<string[]>([]);
  const [state, setState] = useState<SimState | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchPresets().then(setPresets).catch(console.error);

    const disconnect = connectStateStream((payload) => {
      setState(payload);
    });
    return () => disconnect();
  }, []);

  const handleAction = async (cb: () => Promise<void>) => {
    setBusy(true);
    try {
      await cb();
    } finally {
      setBusy(false);
    }
  };

  const start = (payload: RunStartPayload) => handleAction(() => startRun(payload));
  const pause = () => handleAction(pauseRun);
  const resume = () => handleAction(resumeRun);
  const reset = () => handleAction(resetRun);
  const step = (n: number) => handleAction(() => stepRun(n));
  const speed = (hz: number) => handleAction(() => setSpeed(hz));

  return (
    <div className="space-y-8">
      <ControlPanel
        presets={presets}
        state={state ?? undefined}
        onStart={start}
        onPause={pause}
        onResume={resume}
        onReset={reset}
        onStep={step}
        onSpeed={speed}
        busy={busy}
      />
      <MapView state={state ?? undefined} />
    </div>
  );
}
