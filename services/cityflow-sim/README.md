# CityFlow Simulation Service

This microservice wraps the native `cityflow.Engine` loop and exposes a very small internal API that the public `cityflow-api` service talks to. The engine now always uses the real CityFlow bindings – the Docker image installs `CityFlow==0.1` (via CMake + g++) and the server refuses to start a run if the module is missing. Every snapshot is fanned out over both HTTP (`/state`) and WebSocket (`/ws/state`) so the API can subscribe once and rebroadcast to all dashboard clients.

## Endpoints

All routes listen on port `7001` inside the Compose network.

| Method | Path     | Notes |
|--------|----------|-------|
| GET    | `/health` | Basic readiness check. |
| POST   | `/run`    | Body: `{ run_id, config_path, steps, speed_hz?, seed?, thread_num? }`. Starts a new engine instance using the generated config provided by `cityflow-api`. |
| POST   | `/pause`  | Pauses the automatic stepping loop. |
| POST   | `/resume` | Resumes the loop without changing counters. |
| POST   | `/reset`  | Re-initialises the engine for the current run and leaves it paused. |
| POST   | `/step?n=`| Executes `n` manual steps even while paused. |
| POST   | `/speed?hz=` | Updates the loop frequency (1-60 Hz). |
| GET    | `/state`  | Returns the latest snapshot consumed by `/ws/state`. |
| WS     | `/ws/state` | Push stream (10–20 Hz) of `{ state }` payloads for the API bridge. |

Responses use `{ ok: true, ... }` on success, or `{ ok: false, error_code, message }` on descriptive errors so the caller can bubble everything up to the UI consistently. The engine always writes its roadnet/replay logs to the run directory provided by the API (`data/replays/<run_id>/roadnet.json|replay.txt`).

## Local development

```bash
cd services/cityflow-sim
python -m venv .venv
. .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn cityflow_sim.main:create_app --factory --reload --host 0.0.0.0 --port 7001
```

> **Tip:** installing `CityFlow==0.1` requires `cmake` and a C++ toolchain on your machine (or in the Docker image). The provided Dockerfile already installs `build-essential` and compiles the bindings during `pip install -r requirements.txt`.
