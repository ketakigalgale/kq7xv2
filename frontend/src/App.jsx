import { useEffect, useState } from "react";
import { get } from "./api";
import Controls from "./components/Controls";
import DecisionPanel from "./components/DecisionPanel";
import ErrorCharts from "./components/ErrorCharts";
import Kpis from "./components/Kpis";
import MainChart from "./components/MainChart";

function addDays(iso, n) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export default function App() {
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState(null);
  const [day, setDay] = useState(null);
  const [range, setRange] = useState("week");
  const [cutoff, setCutoff] = useState("09:00");
  const [decision, setDecision] = useState(null);
  const [series, setSeries] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [horizon, setHorizon] = useState(null);

  useEffect(() => {
    get("/meta")
      .then((m) => { setMeta(m); setCutoff(m.default_cutoff); setDay(m.delivery_start.slice(0, 8) + "15"); })
      .catch((e) => setError(e.message));
    get("/horizon").then(setHorizon).catch(() => {});
  }, []);

  useEffect(() => {
    if (!meta || !day) return;
    let start = day, end = day;
    if (range === "week") start = addDays(day, -6) < meta.delivery_start ? meta.delivery_start : addDays(day, -6);
    if (range === "month") { start = meta.delivery_start; end = meta.delivery_end; }
    setDecision(null); setSeries(null); setMetrics(null);
    const ac = new AbortController();
    Promise.all([
      get("/decision", { date: day, cutoff }),
      get("/series", { start, end, cutoff }),
      get("/metrics", { start, end, cutoff }),
    ])
      .then(([d, s, m]) => { if (!ac.signal.aborted) { setDecision(d); setSeries(s); setMetrics(m); } })
      .catch((e) => !ac.signal.aborted && setError(e.message));
    return () => ac.abort();
  }, [meta, day, range, cutoff]);

  if (error) {
    return (
      <main className="shell">
        <h1>Wind forecast desk</h1>
        <div className="alert" role="alert">
          <strong>Could not load data.</strong> {error}
        </div>
      </main>
    );
  }

  return (
    <main className="shell">
      <header className="top">
        <div>
          <h1>Wind forecast desk</h1>
          <p className="tagline">GB national wind, forecast against outturn, framed around the day-ahead buying decision.</p>
        </div>
      </header>

      {meta?.source === "synthetic" && (
        <div className="alert warn" role="status">
          Showing synthetic development data, not Elexon data. Run <code>python -m app.fetch</code> to load the real January 2026 data.
        </div>
      )}

      {meta && day && (
        <Controls meta={meta} day={day} setDay={setDay} range={range} setRange={setRange} cutoff={cutoff} setCutoff={setCutoff} />
      )}

      <DecisionPanel d={decision} cutoff={cutoff} />
      <MainChart s={series} />
      <Kpis s={metrics?.summary} />
      <ErrorCharts m={metrics} horizon={horizon} />

      <footer className="foot">
        <p>
          Data: Elexon BMRS, FUELHH (actual wind, half-hourly) and WINDFOR (wind forecasts with publish time). Error is forecast minus actual.
          The forecast shown for each period is the most recent one published at or before the cutoff on the day before delivery.
          The 90% range and the 1-in-20 cover figure use January's own errors, so they are in-sample.
        </p>
      </footer>
    </main>
  );
}
