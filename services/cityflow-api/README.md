# CityFlow API Service

This FastAPI app provides the public REST + WebSocket interface that the Next.js dashboard consumes. It keeps run metadata, metrics and replay logs on disk (`data/replays` and `data/metrics`), prepares preset-specific CityFlow configs (including replay paths and param overrides) and proxies every control action to the private `cityflow-sim` microservice over the Compose network. Every HTTP response is JSON (`{ ok: true/false, ... }`) so the UI never hits `Unexpected end of JSON input`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe. |
| GET | `/scenarios` | Lists preset IDs discovered under `experiments/*.yaml` (fails fast with `INVALID_PRESET`). |
| POST | `/run` | Starts a new run for a preset. Body: `{ id, steps?, speed_hz?, seed?, save_replay? }`. |
| POST | `/pause` | Pauses the automatic stepping loop. |
| POST | `/resume` | Resumes the current run without changing the preset. |
| POST | `/reset` | Resets the engine to the beginning of the active preset. |
| POST | `/step?n=INT` | Steps the engine manually while staying paused. |
| POST | `/speed?hz=INT` | Updates the simulation frequency (1-60 Hz). |
| GET | `/replays` | Lists previous runs (ID, preset, tags, status). |
| GET | `/replays/{run_id}` | Returns recorded frames (`replay.ndjson`) for a run (trim with `?limit=`). |
| GET | `/metrics?run_id=&format=` | JSON or CSV snapshot of the recorded metrics (defaults to latest run/json). |
| GET | `/state` | Last buffered simulator snapshot – HTTP fallback for clients (throttle to ≤2 req/s). |
| POST | `/tags` | Body `{ run_id, tag }` - append a tag. |
| DELETE | `/tags` | Body `{ run_id, tag }` - remove a tag. |
| POST | `/retention` | Body `{ limit }` - adjust the max number of run directories to keep (default 50). |
| WS | `/ws/state` | Broadcasts the simulator WebSocket feed (10–20 Hz fan-out to every UI client). |

## Development

```bash
cd services/cityflow-api
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export DATA_DIR=../../data
export EXPERIMENTS_DIR=../../experiments
export EXAMPLES_DIR=../../examples
export SIM_BASE_URL=http://localhost:7001  # adjust to wherever cityflow-sim runs
uvicorn cityflow_api.main:create_app --factory --reload --host 0.0.0.0 --port 8000
```

Metrics are stored as newline-delimited JSON inside `data/metrics/<run_id>.ndjson`. Replays are newline-delimited JSON snapshots written to `data/replays/<run_id>/replay.ndjson`, together with:

- `run.json` – manifest containing preset, seed, config hash and status. Run folders are named `data/replays/YYYYMMDD_HHMMSS_<preset_id>/`.
- `config.generated.json` – base config + preset overrides + forced absolute replay paths.
- `roadnet.json` / `replay.txt` – emitted by the native CityFlow engine (always enabled).

The API maintains a persistent WebSocket connection to `cityflow-sim` and republishes every frame to dashboard clients. When the stream is interrupted it automatically falls back to a slow HTTP poll (`STATE_POLL_INTERVAL`, default 0.5s) so the UI can keep showing stale-safe data until the socket reconnects.
