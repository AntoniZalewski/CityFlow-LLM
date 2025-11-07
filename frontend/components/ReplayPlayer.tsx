'use client'

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import type { ReplayFrame, RunInfo } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

type ReplayPlayerProps = {
  runs: RunInfo[];
  frames: ReplayFrame[];
  selectedRun?: string | null;
  loading?: boolean;
  onLoad: (runId: string) => Promise<void>;
};

export function ReplayPlayer({
  runs,
  frames,
  selectedRun,
  loading = false,
  onLoad,
}: ReplayPlayerProps) {
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing || frames.length === 0) {
      return;
    }
    const id = setInterval(() => {
      setCursor((prev) => {
        if (prev >= frames.length - 1) {
          return 0;
        }
        return prev + 1;
      });
    }, 200);
    return () => clearInterval(id);
  }, [playing, frames]);

  const currentFrame = frames[cursor];

  const handleRunChange = async (event: React.ChangeEvent<HTMLSelectElement>) => {
    const runId = event.target.value;
    if (!runId) return;
    await onLoad(runId);
    setCursor(0);
    setPlaying(false);
  };

  const timelinePercent =
    frames.length > 1 ? Math.round((cursor / (frames.length - 1)) * 100) : 0;

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
            Replay
          </p>
          <h3 className="text-2xl font-semibold">Time-travel a past run</h3>
        </div>
        <label className="text-sm text-slate-300">
          Run
          <select
            value={selectedRun ?? ""}
            onChange={handleRunChange}
            className="ml-3 rounded-xl border border-white/10 bg-slate-800 px-3 py-2"
          >
            <option value="">Select run</option>
            {runs.map((run) => (
              <option key={run.run_id} value={run.run_id}>
                {run.run_id} - {run.preset_id}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-4">
        <Button
          variant="default"
          disabled={!selectedRun || loading || frames.length === 0}
          onClick={() => setPlaying((value) => !value)}
        >
          {playing ? "Pause" : "Play"}
        </Button>
        <div className="flex-1">
          <Slider
            value={[cursor]}
            onValueChange={(value) => setCursor(value[0])}
            min={0}
            max={Math.max(frames.length - 1, 0)}
            step={1}
            disabled={frames.length === 0}
          />
          <p className="mt-2 text-xs text-slate-400">
            {frames.length > 0 ? `Frame ${cursor + 1} / ${frames.length}` : "No frames"}
            {frames.length > 0 && ` - ${timelinePercent}%`}
          </p>
        </div>
      </div>

      {selectedRun && currentFrame && (
        <div className="mt-6 grid gap-4 rounded-xl border border-white/10 bg-black/30 p-4 md:grid-cols-3">
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-500">Time</p>
            <p className="text-2xl font-semibold">{currentFrame.t}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-500">
              Vehicles
            </p>
            <p className="text-2xl font-semibold">
              {formatNumber(currentFrame.vehicle_count)}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-500">Lanes</p>
            <p className="text-2xl font-semibold">
              {Object.keys(currentFrame.lanes ?? {}).length}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
