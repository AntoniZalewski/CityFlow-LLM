"use client";

import { useEffect, useState } from "react";
import { ReplayPlayer } from "@/components/ReplayPlayer";
import { fetchReplay, fetchRuns } from "@/lib/api";
import type { ReplayFrame, RunInfo } from "@/lib/types";

export default function ReplaysPage() {
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [frames, setFrames] = useState<ReplayFrame[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRuns().then(setRuns).catch(console.error);
  }, []);

  const handleLoad = async (runId: string) => {
    setLoading(true);
    setError(null);
    try {
      const replay = await fetchReplay(runId);
      setFrames(replay.frames ?? []);
      setSelected(runId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load replay");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <ReplayPlayer
        runs={runs}
        frames={frames}
        selectedRun={selected}
        loading={loading}
        onLoad={handleLoad}
      />
      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}
