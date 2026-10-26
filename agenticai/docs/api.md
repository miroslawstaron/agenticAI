# API and configuration reference

Open `/docs` for generated OpenAPI documentation and `/openapi.json` for machine-readable schemas. All routes below use the `/api/v1` prefix. Configuration objects reject unknown fields.

## Local session

GET `/session` returns a process-local token and environment information with `Cache-Control: no-store`. Send `X-Studio-Token: TOKEN` on every mutating request. A supplied Origin must match the server's Host. There is no permissive cross-origin policy. The token changes at server restart. A missing or expired token produces HTTP 403 with `X-Studio-Session: renew` before executing the operation. The web client fetches a fresh token and retries that request once; other authorization errors are not replayed.

## Resources

| Resource | Operations |
|---|---|
| `/providers` | List provider profiles |
| `/providers/{id}` | PUT or DELETE profile |
| `/providers/{id}/models` | GET model discovery, when supported |
| `/providers/{id}/probe` | POST `{model}` to test a completion |
| `/providers/{id}/test` | POST `{model}` to test completion/tool capability |
| `/agents` | List reusable library agents |
| `/agents/{id}` | PUT or DELETE library agent |
| `/networks` and `/networks/{id}` | List, GET, PUT, DELETE |
| `/networks/validate` | POST network for reference and capability checks |
| `/tools` and `/tools/{id}` | List, PUT, DELETE registrations |
| `/tools/{id}/test` | POST argument object and execute tool |
| `/tools/{id}/availability` | GET executable and version check |
| `/plugins` | GET installed Python entry points |
| `/recipes` and `/recipes/{id}` | List and PUT installer recipes |
| `/installations/preview` | POST install request and receive command/fingerprint |
| `/installations` | GET jobs or POST `{request,confirmation}` |
| `/installations/manifest` | GET versioned installed-tool manifest |
| `/installations/restore-preview` | POST manifest; receive reviewable plans |
| `/installations/dockerfile` | GET a derived-image build recipe |
| `/runs` | GET history or POST `{network,prompt?}` |
| `/runs/{id}` | GET snapshot, current network, messages, pending human nodes |
| `/runs/{id}/control/{action}` | POST pause, resume, or cancel |
| `/runs/{id}/human/{agent_id}` | POST `{message}` |
| `/runs/{id}/events` | GET SSE, or `?stream=false&after=SEQ` for a JSON page |
| `/runs/{id}/export/{format}` | GET JSON, CSV, HTML, or optional XLSX |
| `/artifacts/{path}` | GET an artifact from an allowed data subdirectory |
| `/docs` and `/docs/{name}` | List documentation and read Markdown |

## Network contract

A network contains `schema_version`, `id`, `name`, `description`, `mode`, `initial_task`, `agents`, `links`, `entry_agents`, and `limits`. Schema version is currently 1. The optional `initial_task` defaults to an empty string for older configurations. POST `/runs` accepts `{network}` to use the saved initial task, or `{network,prompt}` for a run-specific override; a nonblank task is required. IDs are bounded path-safe identifiers. Entry agents receive the initial task; if omitted, nodes without incoming links become entries. Cyclic networks require explicit entries. The editor's Start node and its connections visualize `initial_task` and `entry_agents`; they are not additional executable agents or communication links.

Each node has a kind: `agent`, `human`, `tool`, or `join`. Agent fields include provider/model, system role, temperature, output/context budgets, tool IDs, topics, orchestration permission, position, and maximum visits. Tool steps use a tool ID and argument object; `${message}` substitutes incoming text in string argument values. Links contain source, target, template, condition, and match value. Communication templates accept `{message}` for the preceding output and `{task}` for the run's original task; inserted content is literal and is not expanded again.

Default limits are four concurrent model calls per run, four tool processes per run, sixteen agents, one hundred model calls, two hundred activations, and 1,200 active seconds. A separate application-wide ceiling of four model calls applies across runs; set `AGENTICAI_CONCURRENCY` before startup to change it (1–64). Provider concurrency defaults to two per endpoint.

## Events and recovery

Events have a monotonic SQLite `seq`, `run_id`, `kind`, timestamp `at`, and JSON `body`. SSE uses `id: SEQ` and a JSON data payload. Reconnect with `Last-Event-ID` or `after`; pages contain at most 1,000 events. A final `end` event closes a completed stream after all stored events are delivered. Event kinds include status, message, delivery, model_call, tool_started, tool_completed, tool_error, human_input, orchestration, network_changed, summary, and run_snapshot.

Run states are queued, running, paused, waiting, completed, failed, cancelled, limited, and interrupted. Restart does not resume side effects. A saved run configuration is immutable; the current network records autonomous changes separately.

## Installation request

```json
{"manager":"pip","package":"ruff","version":"","source":"","action":"install","recipe_id":""}
```

Preview it before POSTing `{request,confirmation}`. Managers are pip, npm, winget, apt, and recipe. Actions are install, update, and remove. Recipes use `${package}`, `${version}`, `${source}`, and other request fields as literal argument substitutions.
