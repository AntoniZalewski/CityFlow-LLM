"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { fetchPresets, fetchRuns, startRun } from "@/lib/api";
import type { RunInfo } from "@/lib/types";
import { formatNumber } from "@/lib/utils";

export default function DashboardPage() {
  const [presets, setPresets] = useState<string[]>([]);
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    refresh();
  }, []);

  const refresh = async () => {
    setError(null);
    try {
      const [presetItems, runItems] = await Promise.all([
        fetchPresets(),
        fetchRuns(),
      ]);
      setPresets(presetItems);
      setRuns(runItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    }
  };

  const handleStart = async (presetId: string) => {
    setLoading(true);
    setError(null);
    try {
      await startRun({ id: presetId });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start run");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-white/10 bg-slate-900/70 p-8 text-slate-50 shadow-xl">
        <p className="text-xs uppercase tracking-[0.4em] text-slate-400">
          Presets
        </p>
        <div className="mt-4 flex flex-wrap gap-4">
          {presets.map((preset) => (
            <div
              key={preset}
              className="flex flex-1 min-w-[220px] items-center justify-between rounded-2xl border border-white/10 bg-black/40 px-4 py-3"
            >
              <div>
                <p className="text-sm text-slate-400">Preset</p>
                <p className="text-lg font-semibold">{preset}</p>
              </div>
              <Button
                size="sm"
                disabled={loading}
                onClick={() => handleStart(preset)}
              >
                Run
              </Button>
            </div>
          ))}
          {presets.length === 0 && (
            <p className="text-sm text-slate-400">
              No presets discovered. Add *.yaml files under /experiments.
            </p>
          )}
        </div>
        {error && (
          <p className="mt-3 text-sm text-red-400" role="alert">
            {error}
          </p>
        )}
      </section>

      <section className="rounded-3xl border border-white/10 bg-slate-900/40 p-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
              Recent runs
            </p>
            <h2 className="text-2xl font-semibold">History</h2>
          </div>
          <Button variant="ghost" asChild>
            <Link href="/replays">Browse replays</Link>
          </Button>
        </div>
        <div className="mt-4 grid gap-3">
          {runs.slice(0, 5).map((run) => (
            <div
              key={run.run_id}
              className="rounded-2xl border border-white/5 bg-white/5 px-4 py-3 text-sm text-slate-200"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-widest text-slate-500">
                    {run.preset_id}
                  </p>
                  <p className="text-lg font-semibold">{run.run_id}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs uppercase tracking-widest text-slate-500">
                    Vehicles
                  </p>
                  <p className="font-semibold">{formatNumber(run.steps)}</p>
                </div>
                <span className="rounded-full bg-white/10 px-3 py-1 text-xs uppercase tracking-wide text-white/80">
                  {run.status}
                </span>
              </div>
            </div>
          ))}
          {runs.length === 0 && (
            <p className="text-sm text-slate-400">
              No runs recorded yet. Launch one of the presets above.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
