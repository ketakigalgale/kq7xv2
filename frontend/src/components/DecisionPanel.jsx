import { dayLabel, hhmm, mw, num, timeLabel } from "../format";

export default function DecisionPanel({ d, cutoff }) {
  if (!d) return <section className="decision skeleton" aria-busy="true" />;
  if (!d.available) {
    return (
      <section className="decision">
        <h2>{dayLabel(d.delivery_date)}</h2>
        <p className="lede">No forecast published before {d.decision_by_local} covers this day. Nothing is substituted.</p>
      </section>
    );
  }
  const sameVintage = d.vintage_first_utc === d.vintage_last_utc;
  return (
    <section className="decision" aria-labelledby="decision-h">
      <div className="decision-head">
        <h2 id="decision-h">Buying for {dayLabel(d.delivery_date)}</h2>
        <p className="lede">
          Bids close at <strong>{d.decision_by_local}</strong>.{" "}
          {sameVintage
            ? <>The latest wind forecast you could see was published <strong>{timeLabel(d.vintage_last_utc)}</strong>.</>
            : <>The latest wind forecasts you could see were published between <strong>{timeLabel(d.vintage_first_utc)}</strong> and <strong>{timeLabel(d.vintage_last_utc)}</strong>.</>}
        </p>
      </div>
      <dl className="facts">
        <div><dt>Expected wind, average</dt><dd>{mw(d.avg_forecast_mw)}</dd></div>
        <div><dt>Expected wind, peak</dt><dd>{mw(d.peak_forecast_mw)}</dd></div>
        <div><dt>Expected wind, trough</dt><dd>{mw(d.min_forecast_mw)}</dd></div>
        <div><dt>Expected energy</dt><dd>{num(d.forecast_mwh)} MWh</dd></div>
        <div className="risk">
          <dt>Cover for a 1-in-20 shortfall</dt>
          <dd>{mw(d.p95_shortfall_mw)}</dd>
          <small>
            On the worst 5% of January half-hours, wind came in this far below forecast. Holding about {num(d.hedge_mwh)} MWh of
            extra thermal cover across the day protects against that.
          </small>
        </div>
        {d.realised_mae_mw !== undefined && (
          <div><dt>Actual error that day</dt><dd>{mw(d.realised_mae_mw)}</dd><small>mean absolute, {mw(d.realised_bias_mw)} bias</small></div>
        )}
      </dl>
      <p className="note">Cutoff used: {cutoff} UK time on the previous day. Change it above to see how much accuracy a later gate closure would buy.</p>
    </section>
  );
}
