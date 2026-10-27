# Wind forecast desk

Day-ahead decision support for a GB utility buying power from the day-ahead market. It answers two questions using
Elexon national wind data only:

1. What is the latest wind forecast available when the day-ahead decision has to be made?
2. How accurate are those forecasts, quantitatively, so the error can be priced into how much extra power to buy?

Scope: purchase decisions made in **January 2026** (delivery days 1 to 31 January 2026, decided on the day before).

**Live app:** `<ADD VERCEL OR HEROKU URL HERE>`
**Video:** `<ADD UNLISTED YOUTUBE URL HERE>`

## AI tools disclosure

This project was built with the assistance of Claude (Anthropic) for code generation, test writing and documentation.
All logic, assumptions and results were reviewed by the author.

## Core method

For delivery day `D`, the forecast for each half-hour is the WINDFOR row with the **greatest `publishTime` that is at or
before the decision cutoff on `D-1`** (default 09:00 UK time, configurable). Anything published later is never used,
so there is no look-ahead. Actuals are FUELHH rows with `fuelType == WIND`.

`error = forecast - actual`. Positive means wind was over-forecast and the buyer is short.

Metrics: MAE, RMSE, bias, weighted MAPE, MAPE (only where actual >= 100 MW), 50/90/95th percentile absolute error, worst
over and under forecast. Breakdowns by UK hour of day, by delivery day, an error histogram, and error versus forecast
horizon across all published vintages.

Planning aid: the 5th and 95th percentile of January decision-time errors give a 90% range around the forecast. The
95th percentile error is shown as "cover for a 1-in-20 shortfall".

### Assumptions to know about

| Assumption | Where | Notes |
|---|---|---|
| Cutoff is 09:00 UK time on D-1 | `DECISION_CUTOFF` env var, or the UI control | GB day-ahead auctions close around 09:20 to 09:50. Confirm with the client. |
| Only timestamps present in both series are scored | `analysis.matched` | If WINDFOR is hourly and FUELHH half-hourly, scoring happens on the shared hourly points. No interpolation. |
| Missing data stays missing | `analysis.build_grid` | The chart shows gaps and counts them. |
| Bands and cover figure are in-sample | `analysis.error_bands` | Calibrated on all of January. For production, use a rolling window of past days only. |
| Forecasts kept up to 96 hours ahead | `MAX_HORIZON_H` | Keeps the cache small. Decision-time forecasts are about 15 to 40 hours ahead. |

## Repository layout

```
Dockerfile              multi-stage: builds React, then Python image serving API + UI
docker-compose.yml      one-command local run
heroku.yml              Heroku container deploy
backend/
  app/config.py         all configuration and assumptions
  app/elexon.py         Elexon API client (FUELHH, WINDFOR), chunking and retries
  app/fetch.py          one-off download to backend/data/*.csv
  app/bootstrap.py      container start hook, fetches only if cache missing
  app/analysis.py       decision-time selection, metrics, breakdowns (pure functions)
  app/main.py           FastAPI routes, serves the built UI
  scripts/make_synthetic.py   synthetic data for UI development only
  tests/                pytest: no-lookahead rule, metrics, API
  data/                 cached Elexon CSVs (commit these after fetching)
frontend/
  src/App.jsx           state and data loading
  src/components/       Controls, DecisionPanel, MainChart, Kpis, ErrorCharts
docs/VIDEO_SCRIPT.md    scripts for the two video parts
.github/workflows/ci.yml
```

## Start the application

### 1. Get the data (once)

```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. python -m app.fetch        # writes backend/data/actuals.csv and forecasts.csv
```

Commit the generated files so deployments do not depend on the live API.

### 2a. Docker

```bash
docker compose up --build
# open http://localhost:8000
```

### 2b. Local development

```bash
# terminal 1
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000
# terminal 2
cd frontend && npm install && npm run dev      # http://localhost:5173, proxies /api to :8000
```

### Tests

```bash
cd backend && PYTHONPATH=. python -m pytest -q
```

### API

| Route | Purpose |
|---|---|
| `GET /api/meta` | Data source, coverage, defaults |
| `GET /api/decision?date=2026-01-15&cutoff=09:00` | Which forecast vintage was available, and the planning numbers |
| `GET /api/series?start=&end=&cutoff=` | Half-hourly actual, decision-time forecast, 90% range, gaps as nulls |
| `GET /api/metrics?start=&end=&cutoff=` | Summary metrics, by hour, by day, histogram |
| `GET /api/horizon` | Error versus hours ahead, all vintages |

## Deploy

**Heroku (single container, UI and API together):**

```bash
heroku create
heroku stack:set container
git push heroku main
```

**Vercel (UI) plus Heroku (API):** deploy `frontend/` to Vercel with env var `VITE_API_URL=https://<your-heroku-app>.herokuapp.com`.
CORS is open for GET requests.

## Submission checklist

- [ ] `python -m app.fetch` run and `backend/data/*.csv` committed
- [ ] README links filled in above
- [ ] Repo name is anonymous (for example `kq7xv2`) and public
- [ ] Unlisted YouTube video under 10 minutes, two parts
- [ ] Every URL opened in incognito
