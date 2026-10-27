from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import analysis as an
from . import config

app = FastAPI(title="Wind forecast decision support", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


@app.exception_handler(an.DataNotAvailable)
async def _no_data(_, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


def _cutoff(cutoff: str | None) -> str:
    c = cutoff or config.DEFAULT_CUTOFF
    try:
        an.parse_cutoff(c)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return c


def _range(start: date | None, end: date | None) -> tuple[date, date]:
    days = an.delivery_days()
    s, e = start or days[0], end or days[-1]
    if s < days[0] or e > days[-1] or s > e:
        raise HTTPException(422, f"Dates must satisfy {days[0]} <= start <= end <= {days[-1]}")
    return s, e


def _month_bands(cutoff: str):
    """Error bands are calibrated on every matched decision-time point in the month (stable, not per-selection)."""
    actuals, _, _ = an.load_data()
    dec = an.decision_frame(cutoff)
    days = an.delivery_days()
    full = an.build_series(actuals, dec, days[0], days[-1])
    return full, an.error_bands(an.matched(full)), dec


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    actuals, fc, source = an.load_data()
    dec = an.decision_frame(config.DEFAULT_CUTOFF)
    days = an.delivery_days()
    return {
        "source": source,
        "delivery_start": days[0].isoformat(),
        "delivery_end": days[-1].isoformat(),
        "default_cutoff": config.DEFAULT_CUTOFF,
        "timezone": config.MARKET_TZ,
        "actual_rows": int(len(actuals)),
        "forecast_rows": int(len(fc)),
        "forecast_vintages": int(fc["publishTime"].nunique()),
        "forecast_step_min": an.forecast_step_minutes(dec),
        "error_convention": "error = forecast - actual; positive means wind was over-forecast (buyer is short)",
    }


@app.get("/api/series")
def series(start: date | None = None, end: date | None = None, cutoff: str | None = Query(None)):
    c = _cutoff(cutoff)
    s, e = _range(start, end)
    full, bands, dec = _month_bands(c)
    d = full[(full["delivery_date"] >= s) & (full["delivery_date"] <= e)]
    step = an.forecast_step_minutes(dec)
    expected_fc = d[d["startTime"].dt.minute % step == 0]
    rows = []
    for r in d.itertuples(index=False):
        f = an._num(r.forecast_mw)
        rows.append({
            "t": r.startTime.isoformat(),
            "actual": an._num(r.actual_mw),
            "forecast": f,
            "lo": an._num(max(f - bands["q95"], 0)) if f is not None else None,
            "hi": an._num(f - bands["q05"]) if f is not None else None,
            "publish": r.publishTime.isoformat() if pd.notna(r.publishTime) else None,
            "horizon_h": an._num(r.horizon_h),
            "error": an._num(r.error_mw),
        })
    return {
        "cutoff": c,
        "bands": {"q05_mw": an._num(bands["q05"]), "q95_mw": an._num(bands["q95"])},
        "forecast_step_min": step,
        "missing_actual": int(d["actual_mw"].isna().sum()),
        "missing_forecast": int(expected_fc["forecast_mw"].isna().sum()),
        "points": rows,
    }


@app.get("/api/metrics")
def metrics(start: date | None = None, end: date | None = None, cutoff: str | None = Query(None)):
    c = _cutoff(cutoff)
    s, e = _range(start, end)
    full, _, _ = _month_bands(c)
    d = full[(full["delivery_date"] >= s) & (full["delivery_date"] <= e)]
    m = an.matched(d)
    return {
        "cutoff": c,
        "summary": an.compute_metrics(m),
        "by_hour": an.by_hour(m),
        "by_day": an.by_day(m),
        "histogram": an.histogram(m),
    }


@app.get("/api/horizon")
def horizon():
    actuals, fc, _ = an.load_data()
    return {"bins": an.horizon_profile(actuals, fc)}


@app.get("/api/decision")
def decision(day: date = Query(..., alias="date"), cutoff: str | None = Query(None)):
    c = _cutoff(cutoff)
    if day not in an.delivery_days():
        raise HTTPException(422, "date outside January 2026 scope")
    full, bands, dec = _month_bands(c)
    return an.decision_summary(full, dec, day, c, bands)


# ----------------------------------------------------------------------------- static frontend (Docker image)
STATIC = Path(__file__).resolve().parent.parent / "static"
if STATIC.exists():
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = STATIC / path
        return FileResponse(f if path and f.is_file() else STATIC / "index.html")
