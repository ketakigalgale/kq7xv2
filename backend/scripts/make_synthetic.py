"""Generate SYNTHETIC data in the same shape as the Elexon cache. For local UI development and tests only.

    DATA_DIR=/tmp/syn python scripts/make_synthetic.py

The output is marked SOURCE=synthetic and the UI shows a banner when it is in use. Never use for the real demo.
"""
import numpy as np
import pandas as pd

from app import config

rng = np.random.default_rng(42)
config.DATA_DIR.mkdir(parents=True, exist_ok=True)

t = pd.date_range("2026-01-01", "2026-02-01", freq="30min", inclusive="left", tz="UTC")
x = np.zeros(len(t)); x[0] = 0.0
for i in range(1, len(t)):
    x[i] = 0.985 * x[i - 1] + rng.normal(0, 0.12)
actual = np.clip(8000 + 5200 * x, 150, 19500)
actuals = pd.DataFrame({"startTime": t, "actual_mw": actual.round(0)})
# punch a few holes so gap handling is exercised
actuals = actuals.drop(actuals.sample(12, random_state=1).index)

rows = []
act_h = pd.Series(actual, index=t)
for pub in pd.date_range("2025-12-28", "2026-02-01", freq="h", inclusive="left", tz="UTC"):
    for h in range(1, config.MAX_HORIZON_H + 1):
        tgt = pub + pd.Timedelta(hours=h)
        if tgt not in act_h.index:
            continue
        sd = 350 + 95 * h
        rows.append((pub, tgt, max(act_h[tgt] + rng.normal(0, sd), 0)))
fc = pd.DataFrame(rows, columns=["publishTime", "startTime", "forecast_mw"]).round(0)

actuals.to_csv(config.ACTUALS_FILE, index=False)
fc.to_csv(config.FORECASTS_FILE, index=False)
config.SOURCE_FILE.write_text("synthetic")
print(len(actuals), len(fc), "->", config.DATA_DIR)
