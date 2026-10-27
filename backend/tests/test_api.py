import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    d = tmp_path_factory.mktemp("data")
    subprocess.run([sys.executable, "scripts/make_synthetic.py"], cwd=ROOT, check=True,
                   env={**os.environ, "PYTHONPATH": str(ROOT), "DATA_DIR": str(d)}, capture_output=True)
    # config is read at import time and other test modules may have imported it already, so patch it.
    from app import analysis, config
    config.DATA_DIR = d
    config.ACTUALS_FILE, config.FORECASTS_FILE, config.SOURCE_FILE = d / "actuals.csv", d / "forecasts.csv", d / "SOURCE"
    analysis.load_data.cache_clear()
    analysis.decision_frame.cache_clear()
    from app.main import app
    return TestClient(app)


def test_meta(client):
    r = client.get("/api/meta").json()
    assert r["source"] == "synthetic" and r["delivery_start"] == "2026-01-01"


def test_series_never_uses_forecast_after_cutoff(client):
    r = client.get("/api/series", params={"start": "2026-01-10", "end": "2026-01-10"}).json()
    pts = [p for p in r["points"] if p["publish"]]
    assert pts, "expected forecasts"
    assert all(p["publish"] <= "2026-01-09T09:00:00+00:00" for p in pts)
    assert len(r["points"]) == 48


def test_metrics_shape(client):
    r = client.get("/api/metrics").json()
    s = r["summary"]
    assert s["n"] > 500 and s["rmse_mw"] >= s["mae_mw"] > 0
    assert len(r["by_hour"]) == 24 and r["histogram"]


def test_later_cutoff_is_more_accurate(client):
    a = client.get("/api/metrics", params={"cutoff": "00:00"}).json()["summary"]["mae_mw"]
    b = client.get("/api/metrics", params={"cutoff": "12:00"}).json()["summary"]["mae_mw"]
    assert b < a


def test_horizon_error_grows(client):
    bins = client.get("/api/horizon").json()["bins"]
    assert bins[0]["mae_mw"] < bins[-1]["mae_mw"]


def test_decision_summary(client):
    r = client.get("/api/decision", params={"date": "2026-01-15"}).json()
    assert r["available"] and r["decision_by_utc"].startswith("2026-01-14T09:00")
    assert r["hedge_mwh"] >= 0


def test_validation(client):
    assert client.get("/api/metrics", params={"cutoff": "9am"}).status_code == 422
    assert client.get("/api/metrics", params={"start": "2026-02-10"}).status_code == 422
    assert client.get("/api/decision", params={"date": "2025-12-31"}).status_code == 422
