import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { TZ, mw, timeLabel } from "../format";

const C = { actual: "#10222B", forecast: "#2457D6", band: "#2457D6" };

function Tip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="tip">
      <strong>{timeLabel(p.t)}</strong>
      <div>Actual: {mw(p.actual)}</div>
      <div>Forecast at cutoff: {mw(p.forecast)}</div>
      {p.error !== null && p.error !== undefined && <div>Error: {mw(p.error)}</div>}
      {p.band && <div>90% range: {mw(p.band[0])} to {mw(p.band[1])}</div>}
      {p.publish && <div>Published {timeLabel(p.publish)} ({Number(p.horizon_h).toFixed(0)} h ahead)</div>}
    </div>
  );
}

export default function MainChart({ s }) {
  if (!s) return <div className="panel skeleton tall" aria-busy="true" />;
  const data = s.points.map((p) => ({
    ...p,
    t: p.t,
    ts: new Date(p.t).getTime(),
    band: p.lo !== null && p.hi !== null ? [p.lo, p.hi] : null,
  }));
  const multiDay = data.length > 96;
  const tick = (v) =>
    new Date(v).toLocaleString("en-GB", multiDay ? { day: "numeric", month: "short", timeZone: TZ } : { hour: "2-digit", minute: "2-digit", timeZone: TZ });
  return (
    <section className="panel" aria-labelledby="chart-h">
      <h3 id="chart-h">Actual wind against the forecast you had at decision time</h3>
      <p className="sub">
        The shaded band is the 90% range implied by January's own forecast errors. Gaps are real: they are periods with no
        {" "}actual or no forecast, and are not interpolated.
        {s.missing_actual > 0 && <> {s.missing_actual} half-hours have no actual.</>}
        {s.missing_forecast > 0 && <> {s.missing_forecast} expected forecast points are missing.</>}
      </p>
      <div className="chart tall">
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
            <CartesianGrid stroke="#D5DCDD" vertical={false} />
            <XAxis dataKey="ts" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={tick} tickCount={multiDay ? 8 : 9} stroke="#5B6B72" />
            <YAxis stroke="#5B6B72" tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} label={{ value: "MW", angle: -90, position: "insideLeft", fill: "#5B6B72" }} />
            <Tooltip content={<Tip />} />
            <Legend verticalAlign="top" height={28} />
            <Area dataKey="band" name="90% range" stroke="none" fill={C.band} fillOpacity={0.14} isAnimationActive={false} connectNulls={s.forecast_step_min > 30} />
            <Line dataKey="forecast" name="Forecast at cutoff" stroke={C.forecast} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={s.forecast_step_min > 30} />
            <Line dataKey="actual" name="Actual" stroke={C.actual} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
