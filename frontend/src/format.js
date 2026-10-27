export const TZ = "Europe/London";

export const mw = (v, d = 0) =>
  v === null || v === undefined ? "n/a" : `${Number(v).toLocaleString("en-GB", { maximumFractionDigits: d })} MW`;

export const num = (v, d = 0) =>
  v === null || v === undefined ? "n/a" : Number(v).toLocaleString("en-GB", { maximumFractionDigits: d });

export const pct = (v, d = 1) => (v === null || v === undefined ? "n/a" : `${Number(v).toFixed(d)}%`);

export const dayLabel = (iso) =>
  new Date(`${iso}T12:00:00Z`).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });

export const timeLabel = (iso) =>
  new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: TZ });

export const hhmm = (iso) =>
  new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: TZ });
