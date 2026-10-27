import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { dayLabel, mw } from "../format";

const axis = { stroke: "#5B6B72", fontSize: 12 };

function Card({ title, sub, children }) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      <p className="sub">{sub}</p>
      <div className="chart">{children}</div>
    </section>
  );
}

export default function ErrorCharts({ m, horizon, dayError }) {
  if (!m) return <div className="grid2"><div className="panel skeleton" /><div className="panel skeleton" /></div>;
  return (
    <div className="grid2">
      <Card title="How big are the misses?" sub="Forecast minus actual. Right of zero means wind came in lower than forecast, which is the costly side for a buyer.">
        <ResponsiveContainer>
          <BarChart data={m.histogram} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#D5DCDD" vertical={false} />
            <XAxis dataKey="mid" {...axis} tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`} />
            <YAxis {...axis} />
            <Tooltip formatter={(v) => [v, "half-hours"]} labelFormatter={(v) => `Error near ${mw(v)}`} />
            <ReferenceLine x={0} stroke="#10222B" />
            <Bar dataKey="count" isAnimationActive={false}>
              {m.histogram.map((b) => <Cell key={b.mid} fill={b.mid > 0 ? "#B4410B" : "#2457D6"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Does accuracy change through the day?" sub="Mean absolute error by UK hour of the target period.">
        <ResponsiveContainer>
          <BarChart data={m.by_hour} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#D5DCDD" vertical={false} />
            <XAxis dataKey="hour" {...axis} />
            <YAxis {...axis} tickFormatter={(v) => `${v}`} />
            <Tooltip formatter={(v, k) => [mw(v), k === "mae_mw" ? "MAE" : "Bias"]} labelFormatter={(h) => `${String(h).padStart(2, "0")}:00 to ${String(h).padStart(2, "0")}:59`} />
            <Bar dataKey="mae_mw" fill="#2457D6" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Which days were hard?" sub="Mean absolute error for each delivery day in the window.">
        <ResponsiveContainer>
          <LineChart data={m.by_day} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#D5DCDD" vertical={false} />
            <XAxis dataKey="date" {...axis} tickFormatter={(d) => d.slice(8)} />
            <YAxis {...axis} />
            <Tooltip formatter={(v) => mw(v)} labelFormatter={dayLabel} />
            <Line dataKey="mae_mw" name="MAE" stroke="#2457D6" strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
            <Line dataKey="bias_mw" name="Bias" stroke="#B4410B" strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <Card title="How much does a later forecast help?" sub="Error of every published forecast in January, grouped by how many hours ahead it was made.">
        {horizon ? (
          <ResponsiveContainer>
            <LineChart data={horizon.bins} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#D5DCDD" vertical={false} />
              <XAxis dataKey="from_h" {...axis} tickFormatter={(v) => `${v}h`} />
              <YAxis {...axis} />
              <Tooltip formatter={(v) => mw(v)} labelFormatter={(h) => `${h} to ${h + 3} hours ahead`} />
              <Line dataKey="mae_mw" name="MAE" stroke="#2457D6" strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : null}
      </Card>
    </div>
  );
}
