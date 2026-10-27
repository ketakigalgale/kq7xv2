"""Container start hook: fetch data if the cache is missing. Never blocks startup on failure."""
from . import config


def main():
    if config.ACTUALS_FILE.exists() and config.FORECASTS_FILE.exists():
        print("Data cache present, skipping fetch.")
        return
    print("Data cache missing, attempting one-off fetch from Elexon ...")
    try:
        from . import fetch
        fetch.main()
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: fetch failed ({exc}). API will report 'no data'. Run `python -m app.fetch` and commit backend/data/.")


if __name__ == "__main__":
    main()
