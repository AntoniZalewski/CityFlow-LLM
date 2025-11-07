'use client'

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import type { RunStartPayload, SimState } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

type ControlPanelProps = {
  presets: string[];
  state?: SimState | null;
  onStart: (payload: RunStartPayload) => Promise<void>;
  onPause: () => Promise<void>;
  onResume: () => Promise<void>;
  onReset: () => Promise<void>;
  onStep: (steps: number) => Promise<void>;
  onSpeed: (hz: number) => Promise<void>;
  busy?: boolean;
};

export function ControlPanel({
  presets,
  state,
  onStart,
  onPause,
  onResume,
  onReset,
  onStep,
  onSpeed,
  busy = false,
}: ControlPanelProps) {
  const [presetId, setPresetId] = useState("");
  const [steps, setSteps] = useState(3600);
  const [seed, setSeed] = useState<number | undefined>(undefined);
  const [saveReplay, setSaveReplay] = useState(true);
  const [speed, setSpeedValue] = useState(10);
  const [stepAmount, setStepAmount] = useState(50);
  const [status, setStatus] = useState<string | null>(null);

  const effectivePresetId = presetId || presets[0] || "";
  const disabled = busy || !effectivePresetId;

  const handleStart = async () => {
    if (!effectivePresetId) return;
    setStatus(null);
    try {
      await onStart({
        id: effectivePresetId,
        steps,
        seed,
        save_replay: saveReplay,
        speed_hz: speed,
      });
      setStatus("Run triggered");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Failed to start run");
    }
  };

  const handleSpeedCommit = async (value: number[]) => {
    const hz = value[0];
    setSpeedValue(hz);
    await onSpeed(hz);
  };

  const handleStep = async () => {
    if (!stepAmount) return;
    await onStep(stepAmount);
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-lg">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-4">
          <label className="block text-sm font-medium text-slate-200">
            Preset
            <select
              className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900/60 px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
              value={effectivePresetId}
              onChange={(event) => setPresetId(event.target.value)}
            >
              {presets.map((preset) => (
                <option key={preset} value={preset}>
                  {preset}
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm text-slate-300">
              Steps
              <Input
                type="number"
                min={1}
                value={steps}
                onChange={(event) => setSteps(Number(event.target.value))}
                className="mt-1"
              />
            </label>
            <label className="text-sm text-slate-300">
              Seed
              <Input
                type="number"
                value={seed ?? ""}
                placeholder="auto"
                onChange={(event) =>
                  setSeed(event.target.value ? Number(event.target.value) : undefined)
                }
                className="mt-1"
              />
            </label>
          </div>
          <label className="inline-flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={saveReplay}
              onChange={(event) => setSaveReplay(event.target.checked)}
            />
            Save replay & metrics
          </label>
        </div>

        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-slate-200">Speed ({speed} Hz)</p>
            <Slider
              value={[speed]}
              min={1}
              max={60}
              step={1}
              onValueChange={(value) => setSpeedValue(value[0])}
              onValueCommit={handleSpeedCommit}
              className="mt-3"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Button
              variant="default"
              disabled={disabled}
              onClick={handleStart}
            >
              Run
            </Button>
            <Button variant="secondary" onClick={onPause} disabled={busy}>
              Pause
            </Button>
            <Button variant="ghost" onClick={onResume} disabled={busy}>
              Resume
            </Button>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Button variant="outline" onClick={onReset} disabled={busy}>
              Reset
            </Button>
            <label className="col-span-2 flex items-center gap-3 text-sm text-slate-300">
              Step
              <Input
                type="number"
                min={1}
                max={10000}
                value={stepAmount}
                onChange={(event) => setStepAmount(Number(event.target.value))}
                className="flex-1"
              />
              <Button variant="secondary" onClick={handleStep} disabled={busy}>
                Go
              </Button>
            </label>
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-6 rounded-2xl border border-white/10 bg-black/20 p-4 md:grid-cols-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-400">Status</p>
          <p className="text-xl font-semibold">
            {state?.status ?? "idle"} | t={state?.t ?? 0}
          </p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-400">
            Vehicles
          </p>
          <p className="text-xl font-semibold">
            {formatNumber(state?.vehicle_count ?? 0)}
          </p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-400">
            Avg waiting (s)
          </p>
          <p className="text-xl font-semibold">
            {formatNumber(state?.metrics_live?.avg_waiting ?? 0, 2)}
          </p>
        </div>
      </div>
      {status && (
        <p className="mt-3 text-sm text-emerald-400" role="status">
          {status}
        </p>
      )}
    </div>
  );
}
