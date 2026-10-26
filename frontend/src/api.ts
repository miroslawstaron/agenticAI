let token = "";
let pendingSession: Promise<any> | null = null;
export async function api<T = any>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  if (method !== "GET" && !token) await session();
  const send = () =>
    fetch("/api/v1" + path, {
      method,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(method === "GET" ? {} : { "X-Studio-Token": token }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  const sentToken = token;
  let response = await send();
  // A server restart invalidates tokens held by open tabs. This response is
  // issued before the operation runs, so renewing and retrying once is safe.
  if (
    response.status === 403 &&
    response.headers.get("X-Studio-Session") === "renew"
  ) {
    if (token === sentToken) await session();
    response = await send();
  }
  if (!response.ok) {
    let message = await response.text();
    try {
      const data = JSON.parse(message);
      message =
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail);
    } catch {}
    throw new Error(message);
  }
  return response.json();
}
export async function session() {
  if (!pendingSession) {
    pendingSession = api("/session")
      .then((value) => {
        token = value.token;
        return value;
      })
      .finally(() => {
        pendingSession = null;
      });
  }
  return pendingSession;
}
export function download(name: string, value: unknown) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
