from datetime import date

import numpy as np
import pandas as pd
import pytest

from app import analysis as an


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def make_fc(rows):
    return pd.DataFrame(rows, columns=["publishTime", "startTime", "forecast_mw"]).assign(
        publishTime=lambda d: pd.to_datetime(d.publishTime, utc=True),
        startTime=lambda d: pd.to_datetime(d.startTime, utc=True),
    )


def test_cutoff_is_previous_day_local_time():
    # January: UK local == UTC
    assert an.cutoff_utc(date(2026, 1, 15), "09:00") == ts("2026-01-14 09:00")
    # Summer: BST is UTC+1, so 09:00 local is 08:00 UTC
    assert an.cutoff_utc(date(2026, 7, 15), "09:00") == ts("2026-07-14 08:00")


def test_bad_cutoff_rejected():
    for bad in ["9:00", "25:00", "09:60", "", "abc"]:
        with pytest.raises(ValueError):
            an.parse_cutoff(bad)


def test_picks_latest_forecast_at_or_before_cutoff_and_never_later():
    target = "2026-01-15 12:00"
    fc = make_fc([
        ("2026-01-13 20:00", target, 100),
        ("2026-01-14 08:00", target, 200),
        ("2026-01-14 09:00", target, 300),   # exactly at cutoff: allowed
        ("2026-01-14 09:30", target, 999),   # after cutoff: must never be used
        ("2026-01-15 06:00", target, 555),   # far after: must never be used
    ])
    out = an.build_decision_forecasts(fc, "09:00")
    assert len(out) == 1
    assert out.forecast_mw.iloc[0] == 300
    assert out.publishTime.iloc[0] == ts("2026-01-14 09:00")
    assert out.horizon_h.iloc[0] == pytest.approx(27.0)


def test_cutoff_override_changes_the_vintage():
    target = "2026-01-15 12:00"
    fc = make_fc([("2026-01-14 08:00", target, 200), ("2026-01-14 09:30", target, 400)])
    assert an.build_decision_forecasts(fc, "09:00").forecast_mw.iloc[0] == 200
    assert an.build_decision_forecasts(fc, "10:00").forecast_mw.iloc[0] == 400


def test_each_delivery_day_uses_its_own_cutoff():
    fc = make_fc([
        ("2026-01-14 08:00", "2026-01-15 00:00", 10),
        ("2026-01-14 08:00", "2026-01-16 00:00", 20),   # D=16 cutoff is Jan 15 09:00, so Jan 14 08:00 is valid
        ("2026-01-15 08:00", "2026-01-16 00:00", 30),
    ])
    out = an.build_decision_forecasts(fc, "09:00").set_index("startTime").forecast_mw
    assert out[ts("2026-01-15 00:00")] == 10
    assert out[ts("2026-01-16 00:00")] == 30


def test_targets_without_any_valid_forecast_are_dropped_not_filled():
    fc = make_fc([("2026-01-15 10:00", "2026-01-15 12:00", 100)])  # published after the D-1 cutoff
    assert an.build_decision_forecasts(fc, "09:00").empty


def test_targets_outside_january_are_excluded():
    fc = make_fc([("2026-01-30 08:00", "2026-02-01 00:00", 1), ("2025-12-30 08:00", "2025-12-31 12:00", 2)])
    assert an.build_decision_forecasts(fc, "09:00").empty


def test_series_keeps_gaps_visible():
    actuals = pd.DataFrame({"startTime": [ts("2026-01-15 00:00")], "actual_mw": [1000.0]})
    dec = an.build_decision_forecasts(make_fc([("2026-01-14 08:00", "2026-01-15 00:30", 1200)]), "09:00")
    s = an.build_series(actuals, dec, date(2026, 1, 15), date(2026, 1, 15))
    assert len(s) == 48
    assert s.actual_mw.notna().sum() == 1 and s.forecast_mw.notna().sum() == 1
    assert an.matched(s).empty  # the two never overlap, so no error is invented


def test_metrics_known_values():
    m = pd.DataFrame({
        "actual_mw": [1000.0, 2000.0, 3000.0, 4000.0],
        "forecast_mw": [1100.0, 1800.0, 3000.0, 4400.0],
    })
    m["error_mw"] = m.forecast_mw - m.actual_mw   # 100, -200, 0, 400
    r = an.compute_metrics(m)
    assert r["n"] == 4
    assert r["mae_mw"] == pytest.approx(175.0)
    assert r["rmse_mw"] == pytest.approx(np.sqrt((100**2 + 200**2 + 0 + 400**2) / 4), rel=1e-3)
    assert r["bias_mw"] == pytest.approx(75.0)
    assert r["wmape_pct"] == pytest.approx(700 / 10000 * 100)
    assert r["max_over_mw"] == 400 and r["max_under_mw"] == -200


def test_mape_ignores_near_zero_actuals():
    m = pd.DataFrame({"actual_mw": [0.0, 1000.0], "forecast_mw": [500.0, 1100.0]})
    m["error_mw"] = m.forecast_mw - m.actual_mw
    r = an.compute_metrics(m)
    assert r["mape_n"] == 1 and r["mape_pct"] == pytest.approx(10.0)


def test_empty_metrics_is_none():
    assert an.compute_metrics(pd.DataFrame(columns=["actual_mw", "forecast_mw", "error_mw"])) is None


def test_error_bands_and_sign_convention():
    m = pd.DataFrame({"error_mw": np.linspace(-100, 300, 101)})
    b = an.error_bands(m)
    assert b["q05"] == pytest.approx(-80, abs=1) and b["q95"] == pytest.approx(280, abs=1)
