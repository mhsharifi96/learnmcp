// Same-origin JSON client for the Django API (session cookie + CSRF header).

export class ApiError extends Error {
  status: number;
  errors: Record<string, string[]>;
  constructor(message: string, status: number, errors: Record<string, string[]> = {}) {
    super(message);
    this.status = status;
    this.errors = errors;
  }
}

function readCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.split("; ").find((c) => c.startsWith(name + "="));
  return match ? decodeURIComponent(match.split("=")[1]) : "";
}

let csrfReady: Promise<void> | null = null;
function ensureCsrf(): Promise<void> {
  if (readCookie("csrftoken")) return Promise.resolve();
  if (!csrfReady) {
    csrfReady = fetch("/api/csrf", { credentials: "same-origin" }).then(() => undefined);
  }
  return csrfReady;
}

export async function api<T = unknown>(
  path: string,
  options: { method?: "GET" | "POST" | "PATCH" | "DELETE"; body?: unknown } = {},
): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") {
    await ensureCsrf();
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = readCookie("csrftoken");
  }
  let res: Response;
  try {
    res = await fetch(`/api/${path}`, {
      method,
      headers,
      credentials: "same-origin",
      body: method === "GET" ? undefined : JSON.stringify(options.body ?? {}),
    });
  } catch {
    throw new ApiError("network", 0);
  }
  let data: any = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    throw new ApiError(data?.error || `HTTP ${res.status}`, res.status, data?.errors || {});
  }
  return data as T;
}
