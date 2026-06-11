# FormulaCast

## Overview

**Description:** This project is an F1 race outcome simulator that generates probabilistic forcast for Formula 1 Grand Prix results

**Method:** Using a Random Forest model that is trained on race data and a Monte Carlo engine that then runs simluated races on top of that baseline

**Goal:** To find a full probabilty distirubtion for every competing driver's finishing position 

**Set Up Instructions:** Use update_season.py to download all seasons from 2018-2026. Once done, run main and test.

## Deployment

FormulaCast is deployed as a split app:

- Vercel hosts the Vite frontend.
- Render hosts the FastAPI backend and runs the model refresh.
- Supabase Storage stores season CSV inputs.

Source season CSVs live in Supabase Storage:

```text
formulacast-data/processed/seasons/season_2018.csv
...
formulacast-data/processed/seasons/season_2026.csv
```

Add these Render environment variables. Do not put the Supabase service role key in the frontend:

```bash
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_BUCKET=formulacast-data
FRONTEND_ORIGIN=https://your-vercel-domain.vercel.app
```

Add this Vercel environment variable:

```bash
VITE_API_BASE_URL=https://your-render-service.onrender.com/api
```

The deployed frontend calls `POST /api/bootstrap` on the Render backend, which downloads the Supabase season files, rebuilds the local feature matrix in temporary runtime storage, trains the model, runs predictions, and returns the generated JSON directly to the app.

Historical prediction JSON is exported to `backend/data/predictions`:

```bash
python -m backend.exporters historical
```

Upcoming/future prediction JSON is exported to `backend/data/predictions/future`:

```bash
python -m backend.exporters future
```

Model performance JSON is exported to `backend/data/predictions/performance.json`:

```bash
python -m backend.exporters performance
```

To rebuild every frontend export at once:

```bash
python -m backend.exporters all
```

When the FastAPI server is connected, the frontend can also trigger a local-only rebuild on page entry:

```bash
POST /api/refresh/local
```

This skips pulling race data, clears the cached local master dataset and feature matrix, rebuilds from the saved local season files, trains the models, runs Monte Carlo, exports JSON, and then the frontend refetches the updated files.

Serve those files to the Vite frontend with FastAPI:

```bash
uvicorn api.main:app --port 8000
```

Avoid `--reload` while using page-entry refreshes. The refresh job writes CSV and JSON files, and Uvicorn's reloader can restart the server in the middle of the job.

By default, the frontend reads `frontend/public/predictions`. To use this backend API instead, create `frontend/.env.local` with:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

In local development, if `VITE_API_BASE_URL` is not set, there is no `/api` request and no backend server is required for the static snapshot. In production, set `VITE_API_BASE_URL` to the Render API URL.

Useful API endpoints:

```bash
GET  /api/health
GET  /api/predictions/races.json
GET  /api/predictions/2026/round_1.json
GET  /api/predictions/future/index.json
GET  /api/predictions/performance.json
POST /api/refresh
POST /api/refresh/local
POST /api/refresh/historical
POST /api/refresh/future
GET  /api/refresh/status
```

`POST /api/refresh` pulls any newly completed rounds, rebuilds historical predictions, rebuilds the next upcoming predictions, and syncs the exported JSON into `frontend/public/predictions` as a static fallback. This should be triggered after race weekends or by a scheduler, not on every page load.

## Strategies Implemented:
- **Random Forest Regression:**  Walk-forward validated model predicting finishing positions from 20+ engineered features, with exponentially weighted rolling averages to capture recent form
- **Monte Carlo Simulation** — 10,000 race iterations with stochastic event modeling:
  - Safety car probability per lap (with first-lap multiplier and cooldown)
  - Mechanical DNF rates per constructor
  - Pit stop time variance and botched stop probability
  - Lap-by-lap overtake attempts based on pace differentials

### Example Output:
```
--- Monte Carlo Results ---
Simulations: 10000

Driver   E[Pos]  Win%  Podium%  Points%  E[Pts]
--------------------------------------------------
VER        2.1   42.3%   81.5%    97.2%   19.84
NOR        3.4   18.7%   58.3%    93.1%   14.22
LEC        4.2   12.1%   44.7%    89.5%   11.67
PIA        5.8    6.3%   25.4%    82.0%    8.93
HAM        6.1    5.2%   22.1%    78.4%    8.12
...
```

## APIs
FormulaCast uses real historical data from the offical F1 timing API via Fastf1

## References:

- [Monte-Carlo](https://en.wikipedia.org/wiki/Monte_Carlo_method)

- [Random-Forest](https://en.wikipedia.org/wiki/Random_forest)
