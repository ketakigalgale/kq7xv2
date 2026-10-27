"""Thin client for the Elexon Insights (BMRS) API. No API key is required.

Endpoints used (stream variants return a bare JSON array):
  FUELHH  /datasets/FUELHH/stream  settlementDateFrom, settlementDateTo, fuelType=WIND
  WINDFOR /datasets/WINDFOR/stream publishDateTimeFrom, publishDateTimeTo
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests

from .config import ELEXON_BASE

TIMEOUT = 60


def _get(path: str, params: dict, retries: int = 4):
    url = f"{ELEXON_BASE}{path}"
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT, headers={"Accept": "application/json"})
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} from {r.url}")
            r.raise_for_status()
            payload = r.json()
            # Stream endpoints return a list; non-stream endpoints wrap it as {"data": [...]}.
            if isinstance(payload, dict):
                payload = payload.get("data", [])
            return payload
        except (requests.RequestException, ValueError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Elexon request failed after {retries} attempts: {last}")


def _chunks(start: date, end: date, days: int):
    cur = start
    while cur <= end:
        nxt = min(cur + timedelta(days=days - 1), end)
        yield cur, nxt
        cur = nxt + timedelta(days=1)


def fetch_actuals(start: date, end: date) -> pd.DataFrame:
    """Half-hourly national wind generation (MW), by settlement date range (inclusive)."""
    rows = []
    for a, b in _chunks(start, end, 7):
        rows += _get(
            "/datasets/FUELHH/stream",
            {"settlementDateFrom": a.isoformat(), "settlementDateTo": b.isoformat(), "fuelType": "WIND"},
        )
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("FUELHH returned no rows. Check the date range and endpoint parameters.")
    df = df[df["fuelType"] == "WIND"]
    out = pd.DataFrame(
        {
            "startTime": pd.to_datetime(df["startTime"], utc=True),
            "actual_mw": pd.to_numeric(df["generation"], errors="coerce"),
        }
    )
    return out.drop_duplicates("startTime").sort_values("startTime").reset_index(drop=True)


def fetch_forecasts(publish_from: date, publish_to: date) -> pd.DataFrame:
    """All wind forecast vintages published in [publish_from, publish_to + 1 day)."""
    rows = []
    for a, b in _chunks(publish_from, publish_to, 2):
        frm = datetime(a.year, a.month, a.day, tzinfo=timezone.utc)
        to = datetime(b.year, b.month, b.day, tzinfo=timezone.utc) + timedelta(days=1)
        rows += _get(
            "/datasets/WINDFOR/stream",
            {
                "publishDateTimeFrom": frm.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "publishDateTimeTo": to.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("WINDFOR returned no rows. Check the date range and endpoint parameters.")
    out = pd.DataFrame(
        {
            "publishTime": pd.to_datetime(df["publishTime"], utc=True),
            "startTime": pd.to_datetime(df["startTime"], utc=True),
            "forecast_mw": pd.to_numeric(df["generation"], errors="coerce"),
        }
    )
    return out.drop_duplicates(["publishTime", "startTime"]).sort_values(["startTime", "publishTime"]).reset_index(drop=True)
