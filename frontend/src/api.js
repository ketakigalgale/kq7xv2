const BASE = import.meta.env.VITE_API_URL || "";

export async function get(path, params = {}) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== ""));
  const res = await fetch(`${BASE}/api${path}${qs.toString() ? `?${qs}` : ""}`);
  if (!res.ok) {
    let detail = `${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch { /* ignore */ }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}
