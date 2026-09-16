const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) ?? "http://localhost:8000/api/v1";

export interface SeriesSpec {
  key: string;
  label: string;
  color: string;
}

export interface VisualizeResponse {
  title: string;
  chart_type: "bar" | "line" | "area" | "horizontal_bar" | "pie";
  x_key: string;
  series: SeriesSpec[];
  data: Record<string, unknown>[];
  insight: string;
  sql: string;
}

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let detail = `Request failed (${r.status})`;
    try { const b = await r.json(); if (b?.detail) detail = b.detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return r.json() as Promise<T>;
}

export function generateVisual(
  prompt: string,
  refine?: string,
  previous_spec?: object,
): Promise<VisualizeResponse> {
  return fetch(`${API_BASE_URL}/visualize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, refine, previous_spec }),
  }).then((r) => j(r));
}
