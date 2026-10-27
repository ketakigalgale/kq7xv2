"""Pure analysis functions. No FastAPI or file IO in here except `load_data`, so everything is unit testable.

Conventions
-----------
* error_mw = forecast_mw - actual_mw.  Positive means the forecast over-stated wind, so the buyer is
  short and must cover the gap (the costly direction when buying day-ahead).
* All timestamps are UTC internally. "Delivery day" and "hour of day" are UK local (Europe/London).
* Decision-time forecast: for delivery day D with cutoff HH:MM, the forecast for each target half-hour is the
  one with the greatest publishTime <= (D-1) HH:MM UK local. Nothing published later is ever used.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

from . import config

TZ = config.MARKET_TZ
_CUTOFF_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class DataNotAvailable(RuntimeError):
    pass


# ----------------------------------------------------------------------------- loading
@lru_cache(maxsize=1)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    if not (config.ACTUALS_FILE.exists() and config.FORECASTS_FILE.exists()):
        raise DataNotAvailable("No cached data found. Run `python -m app.fetch` in backend/ and restart.")
    actuals = pd.read_csv(config.ACTUALS_FILE, parse_dates=["startTime"])
    fc = pd.read_csv(config.FORECASTS_FILE, parse_dates=["startTime", "publishTime"])
    for df, cols in ((actuals, ["startTime"]), (fc, ["startTime", "publishTime"])):
        for c in cols:
            df[c] = pd.to_datetime(df[c], utc=True)
    source = config.SOURCE_FILE.read_text().strip() if config.SOURCE_FILE.exists() else "unknown"
    return actuals, fc, source


# ----------------------------------------------------------------------------- helpers
def parse_cutoff(cutoff: str) -> tuple[int, int]:
    m = _CUTOFF_RE.match(cutoff or "")
    if not m:
        raise ValueError("cutoff must be HH:MM (24h), e.g. 09:00")
    return int(m.group(1)), int(m.group(2))


def delivery_days() -> list[date]:
    d0, d1 = date.fromisoformat(config.DELIVERY_START), date.fromisoformat(config.DELIVERY_END)
    return [d0 + timedelta(days=i) for i in range((d1 - d0).days + 1)]


def cutoff_utc(delivery_day: date, cutoff: str) -> pd.Timestamp:
    """UTC instant of the decision cutoff for a delivery day: (D-1) at HH:MM UK local time."""
    hh, mm = parse_cutoff(cutoff)
    local = datetime.combine(delivery_day - timedelta(days=1), time(hh, mm))
    return pd.Timestamp(local).tz_localize(TZ, ambiguous=True, nonexistent="shift_forward").tz_convert("UTC")


def local_date(ts: pd.Series) -> pd.Series:
    return ts.dt.tz_convert(TZ).dt.date


def _num(x):
    """JSON-safe float."""
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if (np.isnan(x) or np.isinf(x)) else round(x, 3)


# ----------------------------------------------------------------------------- core: decision-time forecast
def build_decision_forecasts(fc: pd.DataFrame, cutoff: str) -> pd.DataFrame:
    """For every target time in the delivery window, pick the latest forecast published at or before the cutoff.

    Returns columns: startTime, publishTime, forecast_mw, delivery_date, cutoff_time, horizon_h
    """
    days = set(delivery_days())
    f = fc.copy()
    f["delivery_date"] = local_date(f["startTime"])
    f = f[f["delivery_date"].isin(days)]
    cutoffs = {d: cutoff_utc(d, cutoff) for d in days}
    f["cutoff_time"] = f["delivery_date"].map(cutoffs)
    f = f[f["publishTime"] <= f["cutoff_time"]]  # the no-lookahead rule
    f = f.sort_values(["startTime", "publishTime"]).drop_duplicates("startTime", keep="last")
    f["horizon_h"] = (f["startTime"] - f["publishTime"]).dt.total_seconds() / 3600
    return f.reset_index(drop=True)


@lru_cache(maxsize=32)
def decision_frame(cutoff: str) -> pd.DataFrame:
    _, fc, _ = load_data()
    return build_decision_forecasts(fc, cutoff)


def forecast_step_minutes(dec: pd.DataFrame) -> int:
    if len(dec) < 2:
        return 30
    step = dec["startTime"].sort_values().diff().dropna().dt.total_seconds().median() / 60
    return int(round(step)) or 30


def build_grid(d_from: date, d_to: date) -> pd.DataFrame:
    """Complete half-hourly grid for the delivery days so gaps stay visible instead of being skipped."""
    lo = pd.Timestamp(d_from).tz_localize(TZ).tz_convert("UTC")
    hi = pd.Timestamp(d_to + timedelta(days=1)).tz_localize(TZ).tz_convert("UTC")
    return pd.DataFrame({"startTime": pd.date_range(lo, hi, freq="30min", inclusive="left")})


def build_series(actuals: pd.DataFrame, dec: pd.DataFrame, d_from: date, d_to: date) -> pd.DataFrame:
    g = build_grid(d_from, d_to)
    g = g.merge(actuals[["startTime", "actual_mw"]], on="startTime", how="left")
    g = g.merge(dec[["startTime", "publishTime", "forecast_mw", "horizon_h"]], on="startTime", how="left")
    g["delivery_date"] = local_date(g["startTime"])
    g["error_mw"] = g["forecast_mw"] - g["actual_mw"]
    return g


def matched(series: pd.DataFrame) -> pd.DataFrame:
    return series.dropna(subset=["actual_mw", "forecast_mw"])


# ----------------------------------------------------------------------------- metrics
def compute_metrics(m: pd.DataFrame) -> dict | None:
    if m.empty:
        return None
    e, a = m["error_mw"], m["actual_mw"]
    ae = e.abs()
    mape_mask = a >= config.MAPE_MIN_ACTUAL_MW
    return {
        "n": int(len(m)),
        "mae_mw": _num(ae.mean()),
        "rmse_mw": _num(np.sqrt((e**2).mean())),
        "bias_mw": _num(e.mean()),
        "wmape_pct": _num(ae.sum() / a.sum() * 100) if a.sum() > 0 else None,
        "mape_pct": _num((ae[mape_mask] / a[mape_mask]).mean() * 100) if mape_mask.any() else None,
        "mape_n": int(mape_mask.sum()),
        "abs_p50_mw": _num(ae.quantile(0.50)),
        "abs_p90_mw": _num(ae.quantile(0.90)),
        "abs_p95_mw": _num(ae.quantile(0.95)),
        "err_p05_mw": _num(e.quantile(0.05)),
        "err_p95_mw": _num(e.quantile(0.95)),
        "max_over_mw": _num(e.max()),
        "max_under_mw": _num(e.min()),
        "mean_actual_mw": _num(a.mean()),
        "mean_forecast_mw": _num(m["forecast_mw"].mean()),
    }


def error_bands(m: pd.DataFrame) -> dict:
    """Empirical 5th and 95th percentile of forecast error, used for the uncertainty band.

    actual = forecast - error, so the 90% interval for actual is [forecast - q95, forecast - q05].
    """
    if m.empty:
        return {"q05": 0.0, "q95": 0.0}
    return {"q05": float(m["error_mw"].quantile(0.05)), "q95": float(m["error_mw"].quantile(0.95))}


def by_hour(m: pd.DataFrame) -> list[dict]:
    if m.empty:
        return []
    h = m["startTime"].dt.tz_convert(TZ).dt.hour
    out = []
    for hour, grp in m.groupby(h):
        out.append({"hour": int(hour), "mae_mw": _num(grp["error_mw"].abs().mean()),
                    "bias_mw": _num(grp["error_mw"].mean()), "n": int(len(grp))})
    return out


def by_day(m: pd.DataFrame) -> list[dict]:
    if m.empty:
        return []
    out = []
    for d, grp in m.groupby("delivery_date"):
        e = grp["error_mw"]
        out.append({"date": d.isoformat(), "mae_mw": _num(e.abs().mean()),
                    "rmse_mw": _num(np.sqrt((e**2).mean())), "bias_mw": _num(e.mean()),
                    "mean_actual_mw": _num(grp["actual_mw"].mean()), "n": int(len(grp))})
    return out


def histogram(m: pd.DataFrame, bins: int = 24) -> list[dict]:
    if len(m) < 2:
        return []
    e = m["error_mw"].to_numpy()
    lim = float(np.ceil(np.abs(e).max() / 100) * 100) or 100.0
    counts, edges = np.histogram(e, bins=bins, range=(-lim, lim))
    return [{"lo": _num(edges[i]), "hi": _num(edges[i + 1]), "mid": _num((edges[i] + edges[i + 1]) / 2),
             "count": int(counts[i])} for i in range(len(counts))]


def horizon_profile(actuals: pd.DataFrame, fc: pd.DataFrame, bin_h: int = 3) -> list[dict]:
    """Accuracy of every published forecast vintage vs. how far ahead it was made. Not limited to the cutoff rule."""
    j = fc.merge(actuals[["startTime", "actual_mw"]], on="startTime", how="inner")
    j["delivery_date"] = local_date(j["startTime"])
    j = j[j["delivery_date"].isin(set(delivery_days()))]
    if j.empty:
        return []
    j["horizon_h"] = (j["startTime"] - j["publishTime"]).dt.total_seconds() / 3600
    j = j[j["horizon_h"] >= 0]
    j["error_mw"] = j["forecast_mw"] - j["actual_mw"]
    j["bin"] = (np.floor(j["horizon_h"] / bin_h) * bin_h).astype(int)
    out = []
    for b, grp in j.groupby("bin"):
        out.append({"from_h": int(b), "to_h": int(b + bin_h), "mae_mw": _num(grp["error_mw"].abs().mean()),
                    "bias_mw": _num(grp["error_mw"].mean()), "n": int(len(grp))})
    return out


# ----------------------------------------------------------------------------- decision summary
def decision_summary(series: pd.DataFrame, dec: pd.DataFrame, day: date, cutoff: str, bands: dict) -> dict:
    d = series[series["delivery_date"] == day]
    f = d.dropna(subset=["forecast_mw"])
    step = forecast_step_minutes(dec)
    out = {
        "delivery_date": day.isoformat(),
        "decision_by_utc": cutoff_utc(day, cutoff).isoformat(),
        "decision_by_local": cutoff_utc(day, cutoff).tz_convert(TZ).strftime("%Y-%m-%d %H:%M %Z"),
        "targets_with_forecast": int(len(f)),
        "forecast_step_min": step,
    }
    if f.empty:
        return {**out, "available": False}
    h = step / 60.0
    buffer_mw = np.minimum(bands["q95"], f["forecast_mw"]).clip(lower=0)
    out.update({
        "available": True,
        "vintage_first_utc": f["publishTime"].min().isoformat(),
        "vintage_last_utc": f["publishTime"].max().isoformat(),
        "vintage_count": int(f["publishTime"].nunique()),
        "avg_forecast_mw": _num(f["forecast_mw"].mean()),
        "peak_forecast_mw": _num(f["forecast_mw"].max()),
        "min_forecast_mw": _num(f["forecast_mw"].min()),
        "forecast_mwh": _num(f["forecast_mw"].sum() * h),
        "p95_shortfall_mw": _num(bands["q95"]),
        "conservative_avg_mw": _num((f["forecast_mw"] - buffer_mw).mean()),
        "hedge_mwh": _num(buffer_mw.sum() * h),
    })
    mm = matched(d)
    if not mm.empty:
        out["realised_mae_mw"] = _num(mm["error_mw"].abs().mean())
        out["realised_bias_mw"] = _num(mm["error_mw"].mean())
    return out
