"""Central configuration. Every assumption lives here and is overridable by env var."""
import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
ACTUALS_FILE = DATA_DIR / "actuals.csv"
FORECASTS_FILE = DATA_DIR / "forecasts.csv"
SOURCE_FILE = DATA_DIR / "SOURCE"  # "elexon" or "synthetic"

ELEXON_BASE = os.getenv("ELEXON_BASE", "https://data.elexon.co.uk/bmrs/api/v1")

# Market timezone. Decisions are expressed in UK local time.
MARKET_TZ = "Europe/London"

# Scope: purchase decisions made in January 2026, i.e. delivery days 2026-01-01 .. 2026-01-31.
# A decision for delivery day D is made on D-1, so for D = 2026-01-01 the decision is on 2025-12-31.
DELIVERY_START = os.getenv("DELIVERY_START", "2026-01-01")
DELIVERY_END = os.getenv("DELIVERY_END", "2026-01-31")

# ASSUMPTION (configurable): the day-ahead decision cutoff on D-1, UK local time, HH:MM.
# GB day-ahead auctions close at roughly 09:20 (EPEX) and 09:50 (N2EX) UK time. We default to 09:00
# so the forecast used is one a trader could realistically have seen and acted on before gate closure.
DEFAULT_CUTOFF = os.getenv("DECISION_CUTOFF", "09:00")

# Only keep forecasts up to this many hours ahead of their target time (keeps the cache small).
MAX_HORIZON_H = int(os.getenv("MAX_HORIZON_H", "96"))

# Forecasts are fetched from this many days before the first delivery day, so D-1 cutoffs are covered.
FORECAST_LOOKBACK_DAYS = 4

# MAPE is unstable when actuals are near zero; only include points above this many MW.
MAPE_MIN_ACTUAL_MW = 100.0
