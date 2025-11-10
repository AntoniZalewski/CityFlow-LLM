"use client";

import type {
  ApiErrorShape,
  MetricsRecord,
  ReplayFrame,
  RunInfo,
  RunResponse,
  RunStartPayload,
  SimState,
} from "@/lib/types";

const API_PREFIX = "/api";

async function parseJson<T>(response: Response): Promise<T> {
  const clone = response.clone();
  let data: unknown = null;
  try {
    data = await response.json();
  } catch (error) {
    const fallback = await clone.text().catch(() => "");
    const suffix = fallback.trim() ? `: ${fallback.trim()}` : "";
    throw new Error(`Unexpected JSON payload (${response.status})${suffix}`);
  }
  if (
    data &&
    typeof data === "object" &&
    (data as ApiErrorShape).ok === false
  ) {
    const err = data as ApiErrorShape;
    throw new Error(err.message ?? "CityFlow API error");
  }
  if (!response.ok) {
    throw new Error(
      (data as Record<string, unknown>)?.message as string ??
        `Request failed (${response.status})`
    );
  }
  return data as T;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      cache: "no-store",
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
  } catch (error) {
    throw new Error("CityFlow API is unreachable. Check docker-compose.");
  }
  return parseJson<T>(response);
}

export async function fetchPresets(): Promise<string[]> {
  const data = await apiFetch<{ items?: string[] }>("/scenarios");
  return Array.isArray(data.items) ? data.items : [];
}

export async function fetchRuns(): Promise<RunInfo[]> {
  const data = await apiFetch<{ items?: RunInfo[] }>("/replays");
  return Array.isArray(data.items) ? data.items : [];
}

export async function startRun(payload: RunStartPayload): Promise<RunResponse> {
  return apiFetch<RunResponse>("/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function pauseRun() {
  await apiFetch("/pause", { method: "POST" });
}

export async function resumeRun() {
  await apiFetch("/resume", { method: "POST" });
}

export async function resetRun() {
  await apiFetch("/reset", { method: "POST" });
}

export async function stepRun(n: number) {
  await apiFetch(`/step?n=${n}`, { method: "POST" });
}

export async function setSpeed(hz: number) {
  await apiFetch(`/speed?hz=${hz}`, { method: "POST" });
}

export async function fetchMetrics(
  runId?: string
): Promise<{ run_id: string; records: MetricsRecord[] }> {
  const params = new URLSearchParams();
  if (runId) params.set("run_id", runId);
  const query = params.toString();
  return apiFetch(`/metrics${query ? `?${query}` : ""}`);
}

export async function fetchMetricsCsv(runId?: string): Promise<string> {
  const params = new URLSearchParams({ format: "csv" });
  if (runId) params.set("run_id", runId);
  const response = await fetch(`/api/metrics?${params.toString()}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Unable to export CSV");
  }
  return response.text();
}

export async function fetchReplay(
  runId: string,
  limit = 1500
): Promise<{ frames: ReplayFrame[]; run_id: string }> {
  return apiFetch<{ frames: ReplayFrame[]; run_id: string }>(
    `/replays/${runId}?limit=${limit}`
  );
}

export async function fetchState(signal?: AbortSignal): Promise<SimState | null> {
  const data = await apiFetch<{ state: SimState | null }>("/state", { signal });
  return data.state ?? null;
}
