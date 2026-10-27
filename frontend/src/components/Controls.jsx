import { dayLabel } from "../format";

export default function Controls({ meta, day, setDay, range, setRange, cutoff, setCutoff }) {
  const days = [];
  const d0 = new Date(`${meta.delivery_start}T00:00:00Z`);
  const d1 = new Date(`${meta.delivery_end}T00:00:00Z`);
  for (let d = new Date(d0); d <= d1; d.setUTCDate(d.getUTCDate() + 1)) days.push(d.toISOString().slice(0, 10));

  return (
    <div className="controls" role="group" aria-label="Analysis controls">
      <label>
        Delivery day
        <select value={day} onChange={(e) => setDay(e.target.value)}>
          {days.map((d) => (
            <option key={d} value={d}>{dayLabel(d)}</option>
          ))}
        </select>
      </label>
      <label>
        Decision cutoff on the day before (UK time)
        <input
          type="time"
          value={cutoff}
          onChange={(e) => e.target.value && setCutoff(e.target.value)}
        />
      </label>
      <fieldset className="seg">
        <legend>Analysis window</legend>
        {[["day", "Selected day"], ["week", "7 days to selected"], ["month", "Whole of January"]].map(([k, label]) => (
          <button key={k} type="button" className={range === k ? "on" : ""} aria-pressed={range === k} onClick={() => setRange(k)}>
            {label}
          </button>
        ))}
      </fieldset>
    </div>
  );
}
