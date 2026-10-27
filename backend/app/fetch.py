"""Download January 2026 data from Elexon and cache it as CSV.

    python -m app.fetch

Run once, then commit backend/data/*.csv so the deployed app never depends on a live API call.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta

import pandas as pd

from . import config, elexon


def main() -> int:
    d0 = date.fromisoformat(config.DELIVERY_START)
    d1 = date.fromisoformat(config.DELIVERY_END)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching FUELHH (WIND) actuals {d0} .. {d1} ...")
    actuals = elexon.fetch_actuals(d0, d1 + timedelta(days=1))

    print("Fetching WINDFOR forecast vintages ...")
    fc = elexon.fetch_forecasts(d0 - timedelta(days=config.FORECAST_LOOKBACK_DAYS), d1)

    # Keep only targets inside the delivery window and a bounded horizon.
    lo = pd.Timestamp(d0, tz=config.MARKET_TZ).tz_convert("UTC")
    hi = pd.Timestamp(d1 + timedelta(days=1), tz=config.MARKET_TZ).tz_convert("UTC")
    fc = fc[(fc.startTime >= lo) & (fc.startTime < hi)]
    horizon_h = (fc.startTime - fc.publishTime).dt.total_seconds() / 3600
    fc = fc[(horizon_h >= 0) & (horizon_h <= config.MAX_HORIZON_H)]
    actuals = actuals[(actuals.startTime >= lo) & (actuals.startTime < hi)]

    actuals.to_csv(config.ACTUALS_FILE, index=False)
    fc.to_csv(config.FORECASTS_FILE, index=False)
    config.SOURCE_FILE.write_text("elexon")
    print(f"actuals: {len(actuals)} rows, forecasts: {len(fc)} rows -> {config.DATA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
