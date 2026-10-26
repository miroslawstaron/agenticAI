import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const source = await readFile(
  new URL("../src/api.ts", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.ES2022,
  },
}).outputText;
let sequence = 0;
const freshApi = () =>
  import(
    `data:text/javascript;base64,${Buffer.from(compiled + `\n// ${sequence++}`).toString("base64")}`
  );
const json = (data) => Response.json(data);
const expired = () =>
  new Response("Missing or invalid local session token", {
    status: 403,
    headers: { "X-Studio-Session": "renew" },
  });

test("first mutation obtains a noncached session before sending", async () => {
  const requests = [];
  globalThis.fetch = async (url, options) => {
    requests.push({ url, options });
    return url.endsWith("/session")
      ? json({ token: "current" })
      : json({ ok: true });
  };
  const { api } = await freshApi();
  await api("/networks/example", "PUT", { initial_task: "Build a program" });
  assert.deepEqual(
    requests.map((r) => r.url),
    ["/api/v1/session", "/api/v1/networks/example"],
  );
  assert.equal(requests[1].options.headers["X-Studio-Token"], "current");
  assert.ok(requests.every((r) => r.options.cache === "no-store"));
});

test("an open tab renews an expired token and executes a run once", async () => {
  let sessions = 0,
    acceptedRuns = 0,
    rejectedRuns = 0;
  globalThis.fetch = async (url, options) => {
    if (url.endsWith("/session"))
      return json({ token: ++sessions === 1 ? "old" : "new" });
    if (options.headers["X-Studio-Token"] !== "new") {
      rejectedRuns++;
      return expired();
    }
    acceptedRuns++;
    assert.equal(JSON.parse(options.body).prompt, "my task");
    return json({ id: "run" });
  };
  const { api, session } = await freshApi();
  await session();
  assert.deepEqual(await api("/runs", "POST", { prompt: "my task" }), {
    id: "run",
  });
  assert.deepEqual(
    { sessions, acceptedRuns, rejectedRuns },
    { sessions: 2, acceptedRuns: 1, rejectedRuns: 1 },
  );
});

test("simultaneous stale requests share one session renewal", async () => {
  let sessions = 0;
  globalThis.fetch = async (url, options) => {
    if (url.endsWith("/session")) {
      const token = ++sessions === 1 ? "old" : "new";
      await new Promise((resolve) => setTimeout(resolve, 5));
      return json({ token });
    }
    return options.headers["X-Studio-Token"] === "new"
      ? json({ ok: true })
      : expired();
  };
  const { api, session } = await freshApi();
  await session();
  await Promise.all([
    api("/networks/a", "PUT", {}),
    api("/networks/b", "PUT", {}),
  ]);
  assert.equal(sessions, 2);
});

test("ordinary authorization errors are never replayed", async () => {
  let mutations = 0,
    sessions = 0;
  globalThis.fetch = async (url) => {
    if (url.endsWith("/session")) {
      sessions++;
      return json({ token: "current" });
    }
    mutations++;
    return new Response("Cross-origin requests are not allowed", {
      status: 403,
    });
  };
  const { api } = await freshApi();
  await assert.rejects(api("/runs", "POST", {}), /Cross-origin/);
  assert.equal(mutations, 1);
  assert.equal(sessions, 1);
});

test("persistent token rejection stops after one retry", async () => {
  let mutations = 0;
  globalThis.fetch = async (url) => {
    if (url.endsWith("/session")) return json({ token: "current" });
    mutations++;
    return expired();
  };
  const { api } = await freshApi();
  await assert.rejects(api("/runs", "POST", {}), /session token/);
  assert.equal(mutations, 2);
});
