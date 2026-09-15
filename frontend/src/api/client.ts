// All HTTP calls to the backend go through this module and its siblings in
// src/api/ — see ../../architecture/FRONTEND_ARCHITECTURE.md#layering.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type QueryParams = Record<string, string | number | boolean | undefined | null>;

function toQuery(params?: QueryParams): string {
  if (!params) return "";
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) sp.append(key, String(value));
  }
  const q = sp.toString();
  return q ? `?${q}` : "";
}

export async function apiGet<T>(path: string, params?: QueryParams): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}${toQuery(params)}`);
  if (!response.ok) {
    throw new ApiError(`GET ${path} failed with status ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}
