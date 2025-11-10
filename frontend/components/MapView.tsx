'use client'

import type { SimState } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

type MapViewProps = {
  state?: SimState | null;
};

export function MapView({ state }: MapViewProps) {
  const lanes = Object.entries(state?.lanes ?? {}).slice(0, 12);

  return (
    <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900/60 to-black/60 p-6 text-slate-100 shadow-inner">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
            Live telemetry
          </p>
          <h2 className="text-2xl font-semibold tracking-tight">
            {state?.run_id ? `Run ${state.run_id}` : "No active run"}
          </h2>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-widest text-slate-500">
            Time step
          </p>
          <p className="text-3xl font-black">{state?.t ?? 0}</p>
        </div>
      </div>

      {lanes.length === 0 ? (
        <p className="text-sm text-slate-400">
          Waiting for state samples. Start a run to populate the live view.
        </p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {lanes.map(([laneId, lane]) => {
            const loadFactor = Math.min(1, lane.vehicles / 50);
            return (
              <div
                key={laneId}
                className="rounded-xl border border-white/10 bg-slate-900/70 p-3"
              >
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  {laneId}
                </p>
                <div className="mt-2 h-2 rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-cyan-400 transition-all"
                    style={{ width: `${loadFactor * 100}%` }}
                  />
                </div>
                <div className="mt-2 flex justify-between text-xs text-slate-300">
                  <span>{formatNumber(lane.vehicles)} vehicles</span>
                  <span>{formatNumber(lane.waiting)} waiting</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
