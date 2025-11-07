"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { MetricsChart } from "@/components/MetricsChart";
import { fetchMetrics, fetchRuns } from "@/lib/api";
import type { MetricsSeries, RunInfo } from "@/lib/types";

export default function MetricsPage() {
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [series, setSeries] = useState<MetricsSeries>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchRuns()
      .then((items) => {
        setRuns(items);
        if (items[0]) {
          setSelected([items[0].run_id]);
          loadMetrics(items[0].run_id);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load runs"));
  }, []);

  const loadMetrics = async (runId: string) => {
    setLoading(true);
    try {
      const result = await fetchMetrics(runId);
      setSeries((prev) => ({
        ...prev,
        [runId]: result.records,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch metrics");
    } finally {
      setLoading(false);
    }
  };

  const toggleRun = (runId: string) => {
    setSelected((prev) => {
      if (prev.includes(runId)) {
        return prev.filter((id) => id !== runId);
      }
      if (prev.length >= 3) {
        return prev;
      }
      loadMetrics(runId);
      return [...prev, runId];
    });
  };

  const selectedSeries = useMemo(() => {
    const entries: MetricsSeries = {};
    selected.forEach((runId) => {
      if (series[runId]) {
        entries[runId] = series[runId];
      }
    });
    return entries;
  }, [selected, series]);

  const download = (content: string, filename: string, type: string) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const exportJson = () => {
    if (selected.length === 0) {
      setError("Select at least one run to export.");
      return;
    }
    const payload = selected.map((runId) => ({
      run_id: runId,
      records: series[runId] ?? [],
    }));
    download(JSON.stringify(payload, null, 2), "metrics.json", "application/json");
  };

  const exportCsv = () => {
    if (selected.length === 0) {
      setError("Select at least one run to export.");
      return;
    }
    const header = "run_id,t,vehicle_count,avg_speed,avg_waiting,throughput";
    const rows = [header];
    selected.forEach((runId) => {
      (series[runId] ?? []).forEach((record) => {
        rows.push(
          [
            runId,
            record.t,
            record.vehicle_count,
            record.avg_speed ?? "",
            record.avg_waiting ?? "",
            record.throughput ?? "",
          ].join(",")
        );
      });
    });
    download(rows.join("\n"), "metrics.csv", "text/csv");
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-white/10 bg-slate-900/70 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
              Runs
            </p>
            <h2 className="text-2xl font-semibold">Pick up to three runs</h2>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={exportJson} disabled={selected.length === 0}>
              Export JSON
            </Button>
            <Button variant="ghost" onClick={exportCsv} disabled={selected.length === 0}>
              Export CSV
            </Button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {runs.map((run) => {
            const active = selected.includes(run.run_id);
            return (
              <button
                key={run.run_id}
                onClick={() => toggleRun(run.run_id)}
                className={`rounded-full px-4 py-2 text-sm transition ${
                  active
                    ? "bg-white text-slate-900"
                    : "bg-white/10 text-white hover:bg-white/20"
                }`}
              >
                {run.run_id}
              </button>
            );
          })}
        </div>
        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
      </section>
      <MetricsChart title="Vehicle count" metric="vehicle_count" series={selectedSeries} />
      <MetricsChart title="Average waiting time" metric="avg_waiting" series={selectedSeries} />
      {loading && <p className="text-sm text-slate-400">Loading metrics...</p>}
    </div>
  );
}
