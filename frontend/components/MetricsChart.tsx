'use client'

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
  CartesianGrid,
} from "recharts";
import type { MetricsRecord, MetricsSeries } from "@/lib/types";

type MetricsChartProps = {
  series: MetricsSeries;
  metric: keyof Pick<MetricsRecord, "vehicle_count" | "avg_waiting" | "throughput">;
  title: string;
};

const COLORS = ["#06b6d4", "#f97316", "#a855f7"];

export function MetricsChart({ series, metric, title }: MetricsChartProps) {
  const runIds = Object.keys(series);
  const data = mergeSeries(series, metric);

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
            Metric
          </p>
          <h3 className="text-2xl font-semibold">{title}</h3>
        </div>
        <p className="text-sm text-slate-400">
          {runIds.length === 0
            ? "Select runs to compare"
            : `Comparing ${runIds.length} run${runIds.length > 1 ? "s" : ""}`}
        </p>
      </div>
      <div className="mt-4 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="4 4" stroke="#1e293b" />
            <XAxis
              dataKey="t"
              stroke="#94a3b8"
              tickLine={false}
              fontSize={12}
            />
            <YAxis stroke="#94a3b8" tickLine={false} fontSize={12} />
            <Tooltip
              contentStyle={{ background: "#020617", borderRadius: 12 }}
              labelStyle={{ color: "#e2e8f0" }}
            />
            <Legend />
            {runIds.map((runId, index) => (
              <Line
                key={runId}
                type="monotone"
                dataKey={`${runId}-${metric}`}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={false}
                name={`${runId} ${metric}`}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function mergeSeries(series: MetricsSeries, metric: string) {
  const byTime = new Map<
    number,
    {
      t: number;
      [key: string]: number | null;
    }
  >();

  Object.entries(series).forEach(([runId, records]) => {
    records.forEach((record) => {
      const bucket = byTime.get(record.t) ?? { t: record.t };
      const value = (record as Record<string, number | null>)[metric];
      bucket[`${runId}-${metric}`] = value ?? 0;
      byTime.set(record.t, bucket);
    });
  });

  return Array.from(byTime.values()).sort((a, b) => a.t - b.t);
}
