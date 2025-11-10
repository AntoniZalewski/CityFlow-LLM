export type PresetId = string;

export interface ApiErrorShape {
  ok: false;
  error_code?: string;
  message?: string;
}

export interface RunStartPayload {
  id: string;
  steps?: number;
  speed_hz?: number;
  seed?: number;
  save_replay?: boolean;
}

export interface RunResponse {
  ok: true;
  run_id: string;
  preset_id: string;
  started_at: string;
  speed_hz: number;
}

export interface RunInfo {
  run_id: string;
  preset_id: string;
  started_at: string;
  steps: number;
  speed_hz: number;
  seed: number;
  save_replay: boolean;
  status: string;
  tags: string[];
}

export interface LiveMetrics {
  avg_speed?: number | null;
  avg_waiting?: number | null;
  throughput?: number | null;
}

export interface LaneSnapshot {
  vehicles: number;
  waiting: number;
}

export interface SimState {
  t: number;
  run_id?: string | null;
  status: string;
  vehicle_count: number;
  lanes: Record<string, LaneSnapshot>;
  signals?: Record<string, unknown>;
  metrics_live?: LiveMetrics;
  speed_hz?: number;
}

export interface MetricsRecord {
  t: number;
  vehicle_count: number;
  avg_speed?: number | null;
  avg_waiting?: number | null;
  throughput?: number | null;
}

export interface MetricsSeries {
  [runId: string]: MetricsRecord[];
}

export interface ReplayFrame {
  t: number;
  vehicle_count: number;
  lanes: Record<string, LaneSnapshot>;
  status: string;
}
