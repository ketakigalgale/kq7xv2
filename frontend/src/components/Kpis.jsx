import { mw, num, pct } from "../format";

export default function Kpis({ s, n }) {
  if (!s) return <div className="kpis skeleton" aria-busy="true" />;
  const items = [
    ["Mean absolute error", mw(s.mae_mw), "Typical miss per half-hour"],
    ["RMSE", mw(s.rmse_mw), "Penalises large misses"],
    ["Bias", mw(s.bias_mw), s.bias_mw > 0 ? "Forecast runs high: wind under-delivers" : "Forecast runs low: wind over-delivers"],
    ["Weighted error", pct(s.wmape_pct), "Absolute error as share of total wind"],
    ["90th percentile miss", mw(s.abs_p90_mw), "9 in 10 half-hours miss by less"],
    ["95th percentile miss", mw(s.abs_p95_mw), "19 in 20 half-hours miss by less"],
    ["Worst over-forecast", mw(s.max_over_mw), "Largest shortfall against forecast"],
    ["Compared points", num(s.n), `MAPE ${pct(s.mape_pct)} on ${num(s.mape_n)} points above 100 MW`],
  ];
  return (
    <section aria-label="Accuracy summary" className="kpis">
      {items.map(([k, v, sub]) => (
        <div className="kpi" key={k}>
          <div className="kpi-v">{v}</div>
          <div className="kpi-k">{k}</div>
          <div className="kpi-s">{sub}</div>
        </div>
      ))}
    </section>
  );
}
