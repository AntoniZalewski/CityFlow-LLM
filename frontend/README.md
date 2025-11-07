## CityFlow Frontend

Next.js 14 dashboard that drives the CityFlow simulation stack. It exposes four main screens:

- **Dashboard** - launch presets and review recent runs.
- **Live** - real-time control panel (run, pause, reset, step, tune Hz) + WebSocket telemetry and lane heat-map.
- **Replays** - browse historical runs and scrub through recorded frames.
- **Metrics** - compare metrics for up to three runs and export CSV/JSON bundles.

### Commands

```bash
npm install        # install deps
npm run dev        # start local dev server on http://localhost:3000
npm run build      # production build
npm start          # serve the production build
```

The UI proxies every `/api/*` call to the FastAPI service. Configure the backend origin via:

```
API_BASE=http://cityflow-api:8000             # used on the server (Next.js API routes)
NEXT_PUBLIC_API_BASE=http://localhost:8000    # optional fallback if API_BASE is not set
NEXT_PUBLIC_WS_STATE_URL=ws://localhost:8000/ws/state   # override only when the default doesn't work
```

### WebSocket

By default the browser connects to `ws://localhost:8000/ws/state`, which is the FastAPI fan-out of the simulator stream (10–20 Hz). If the socket drops or is blocked the client automatically falls back to polling `GET /api/state` every 500 ms so the dashboard never crashes with `Unexpected end of JSON input`.

Each payload contains:

```json
{
  "t": 640,
  "run_id": "20241107_154200_nyc_grid_baseline",
  "status": "running",
  "vehicle_count": 128,
  "lanes": {
    "lane_0": { "vehicles": 4, "waiting": 1 }
  },
  "metrics_live": {
    "avg_speed": 9.8,
    "avg_waiting": 1.3,
    "throughput": 12.4
  },
  "speed_hz": 10
}
```

### REST interactions

All fetch helpers live in `lib/api.ts` and hit the FastAPI contracts described in `services/cityflow-api/README.md` (run control, replay listing, metrics export, tag management).
