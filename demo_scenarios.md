# Demonstration scenarios for AgenticAI Studio

These scenarios exercise the agent networks implemented in this repository: bounded feedback, specialist handoffs, tool execution, autonomous delegation, human input, conditional routing, parallel branches, artifacts, and execution limits.

## Current setup

Inspected on 23 October 2026:

- Studio is running at <http://127.0.0.1:8876>, using `.build/studio-data` on the Windows host.
- The four seeded networks are **Teacher & student**, **Designer & programmer**, **C verification**, and **Autonomous team**.
- Only the **Demo provider** (`provider_id: demo`, `model: demo`) is configured. It returns scripted responses, repeats part of its input, emits a fixed hello-world program for the C programmer, and scripts one assistant spawn for an orchestrator. It does not solve arbitrary tasks or perform external research.
- Python and GCC are available to the backend. `cppcheck` is currently unavailable. Scenario 3 explains how to demonstrate this explicitly or run compilation alone.
- Registered tools are `compiler`, `analyzer`, `shell`, and `python-version`. The scenarios below do not require shell access.

Use the demo provider for a repeatable demonstration of execution and communication. For substantive generated solutions, configure a compatible HTTP provider in **Model providers**, test it, and set both the provider and a served model name on each AI node. Autonomous orchestration requires tool calling. A successful plain connection test alone does not establish that a model supports tool calling.

If Studio needs restarting, run this from the repository root in a separate PowerShell window:

```powershell
.\.venv\Scripts\python.exe -m agenticai serve --port 8876 --data .build/studio-data
```

The CLI and server must use different data directories if running simultaneously. For a Docker deployment, use its published address, normally <http://127.0.0.1:8765>, and check tool availability inside that container.

## Presenter setup

Scenarios 1–4 use existing networks. Select the named network, enter the supplied prompt in **TASK PROMPT**, and click **Run network**. Inspect **Activity**, then **Run history**. The PowerShell alternatives below also provide exact, repeatable configurations for scenarios 5–8.

Paste these helpers once into a PowerShell terminal. They acquire the session token required for API writes. `Start-Demo` validates and saves a scenario, then starts it. Copies use `demo-*` IDs so seeded networks retain their original configurations. Repeating a scenario replaces its saved demo configuration and creates a new run record.

```powershell
$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8876'
$session = Invoke-RestMethod "$base/api/v1/session"
$headers = @{ 'X-Studio-Token' = $session.token }

function Copy-DemoNetwork([string]$Id) {
    $network = Invoke-RestMethod "$base/api/v1/networks/$Id"
    $network.id = "demo-$Id"
    $network.name = "Demo - $($network.name)"
    return $network
}

function Start-Demo($Network, [string]$Prompt) {
    $json = $Network | ConvertTo-Json -Depth 40
    $validation = Invoke-RestMethod "$base/api/v1/networks/validate" `
        -Method Post -Headers $headers -ContentType 'application/json' -Body $json
    if (-not $validation.valid) { throw ($validation.errors -join '; ') }
    Invoke-RestMethod "$base/api/v1/networks/$($Network.id)" `
        -Method Put -Headers $headers -ContentType 'application/json' -Body $json | Out-Null
    $body = @{ network = $Network; prompt = $Prompt } | ConvertTo-Json -Depth 40
    $run = Invoke-RestMethod "$base/api/v1/runs" `
        -Method Post -Headers $headers -ContentType 'application/json' -Body $body
    Write-Host "Run $($run.id): refresh Studio, open Run history, and select this run."
    return $run.id
}

function Get-DemoEvents([string]$RunId) {
    $events = Invoke-RestMethod "$base/api/v1/runs/$RunId/events?stream=false"
    foreach ($event in $events) { $event }
}
```

Refresh Studio after an API-created scenario to see its saved network and run. Run the scenarios individually; each code block assigns its own `$network` and `$runId`. If Studio restarts, paste the helpers again to obtain its new session token.

| Scenario | What to demonstrate | Requirements | Suggested time |
| --- | --- | --- | --- |
| 1. Feedback loop | Two rounds with explicit termination | Demo provider | 2 min |
| 2. Specialist handoff | Design passed to implementation | Demo provider; live model for task-specific code | 2 min |
| 3. C verification | Parallel compiler/analyzer tools and diagnostics | GCC; cppcheck for both successful branches | 3 min |
| 4. Autonomous team | Child creation, delegation, evolved graph | Demo provider or tool-capable live model | 3 min |
| 5. Human decision | Waiting, approval/rejection, conditional links | Demo provider | 3 min |
| 6. Parallel review | Two reviewers, join, single synthesis | Demo provider | 3 min |
| 7. CLI artifact | Real execution, structured output, downloadable report | Backend Python | 3 min |
| 8. Execution budget | Predictable stop at a model-call limit | Demo provider | 2 min |

Times include presenter explanation; demo-provider runs usually finish too quickly to watch each step live. Use the recorded timeline. A compact presentation can use scenarios 1, 4, 5, and 7.

## 1. Two rounds of student/teacher feedback

**Network:** `student -> teacher -> student -> teacher` in workflow mode. Student is the entry node; both nodes have `max_visits: 2`.

**Prompt:**

> Explain binary search to a first-year programming student. Include its invariant, time complexity, and one common boundary error. The teacher should identify gaps and the student should revise the explanation.

```powershell
$network = Copy-DemoNetwork 'teacher-student'
$runId = Start-Demo $network 'Explain binary search to a first-year programming student. Include its invariant, time complexity, and one common boundary error. The teacher should identify gaps and the student should revise the explanation.'
```

**Show:** Four `agent_completed` events, alternating Student, Teacher, Student, Teacher. The next attempted Student activation produces `visit_limit`, and the run finishes `completed`. There are four model calls with the demo provider.

**Talking point:** Links carry the previous output, while each agent retains its own conversation history. Visit limits bound a feedback loop. The final output here is the teacher's second feedback; use a live model to discuss the quality of revisions.

**Reset:** Start another run; each run begins with fresh agent histories and visit counters.

## 2. Designer hands a specification to a programmer

**Network:** `designer -> programmer`, with Designer as entry.

**Prompt:**

> Design and implement a C11 program that converts Celsius to Fahrenheit. Read one number, reject invalid input, and print the result to two decimal places. The designer should specify behavior and test cases; the programmer should return one complete fenced C program.

```powershell
$network = Copy-DemoNetwork 'designer-programmer'
$runId = Start-Demo $network 'Design and implement a C11 program that converts Celsius to Fahrenheit. Read one number, reject invalid input, and print the result to two decimal places. The designer should specify behavior and test cases; the programmer should return one complete fenced C program.'
```

**Show:** Designer completes before Programmer starts. Inspect the message delivered to Programmer and its C code block. With the demo provider, the program always prints `Hello from AgenticAI`; task-specific conversion logic requires a live model.

**Talking point:** Separate roles make the handoff visible. The programmer has compiler/analyzer tools available, but those are optional model calls, and the demo provider does not invoke them. This network does not guarantee verification; scenario 3 adds mandatory tool nodes.

**Live-model extension:** Configure different served models for Designer and Programmer to compare specialization. Keep the same prompt and compare saved runs.

## 3. Compile and analyze C in parallel

**Network:** `programmer -> compile` and `programmer -> analyze`. Both tool nodes receive the same C program using `{"code":"${message}"}`.

**Prompt:**

> Return a complete C11 program in one fenced C code block. Print a greeting and return zero. Do not include any other code blocks.

```powershell
$network = Copy-DemoNetwork 'compiler-analyzer'
$runId = Start-Demo $network 'Return a complete C11 program in one fenced C code block. Print a greeting and return zero. Do not include any other code blocks.'
```

**Show on the current host:** Analyze reports `Executable not found: cppcheck`. With the current source, a failed mandatory tool node makes the run `failed` and may cancel its sibling branch before compilation finishes. Use the compiler-only copy below to show successful compilation and its `program.c`, binary, and log artifacts. The compiler builds the program but does not execute it.

**Important interpretation:** Inspect every `tool_completed` result before claiming the code passed verification. An older Studio process may still report `completed` after a tool failure; restart Studio to load the current source behavior. The diagram does not contain a repair loop.

For a successful compiler-only demonstration with the current setup, run this separate copy:

```powershell
$network = Copy-DemoNetwork 'compiler-analyzer'
$network.id = 'demo-compile-only'
$network.name = 'Demo - Compile only'
$network.agents = @($network.agents | Where-Object { $_.id -ne 'analyze' })
$network.links = @($network.links | Where-Object { $_.target -ne 'analyze' })
($network.agents | Where-Object { $_.id -eq 'programmer' }).tools = @('compiler')
$runId = Start-Demo $network 'Return one complete fenced C11 hello-world program.'
```

To demonstrate a guaranteed compiler diagnostic without relying on generated output, test the compiler directly with invalid C:

```powershell
$body = @{ code = 'int main(void) { return 0 }' } | ConvertTo-Json
Invoke-RestMethod "$base/api/v1/tools/compiler/test" `
    -Method Post -Headers $headers -ContentType 'application/json' -Body $body
```

Expect `ok: false`, a nonzero exit code, and a diagnostic about the missing semicolon. This is a direct tool test, not an agent run.

**Full verification prerequisite:** Make `cppcheck` available to the backend, restart it if its PATH changed, and confirm availability in **Tools & CLI** before presenting two successful branches. The repository's Dockerfile includes GCC and cppcheck; host installations and container installations are separate.

## 4. Autonomous delegation and an evolved network

**Network:** One Coordinator entry node in autonomous mode, with orchestration enabled.

**Prompt:**

> Prepare a short briefing comparing fixed workflows with autonomous agent teams. Delegate a focused subtask to a research assistant, review its response, and provide a concise synthesis. Use only the supplied task and general knowledge; no web research is required.

```powershell
$network = Copy-DemoNetwork 'autonomous-team'
$runId = Start-Demo $network 'Prepare a short briefing comparing fixed workflows with autonomous agent teams. Delegate a focused subtask to a research assistant, review its response, and provide a concise synthesis. Use only the supplied task and general knowledge; no web research is required.'
```

**Show:** A `network_changed` event with action `spawn_agent`, a new **Research assistant**, task delivery to that assistant, and a delegated result delivered back to Coordinator. The demo provider produces two nodes and four model calls in total. It demonstrates the delegation mechanism with scripted text.

Click **Use evolved network** after completion to inspect the two-node graph and reciprocal links. This loads a new, unsaved copy; click **Save** to retain it. The original single-node snapshot remains attached to the historical run.

**Talking point:** In autonomous mode, links authorize communication; they do not automatically forward every completed response. Orchestration calls enqueue work. Spawned children inherit the parent provider/model and can receive only a subset of the parent's tools. There is no browser or research tool configured in this setup.

**Reset:** Select the original **Autonomous team** for another single-node start, rather than the evolved graph.

## 5. Human approval and conditional routing

**Network:** `draft -> review`, then `review -> accepted` or `review -> rejected`. The Human input node forwards the person's response verbatim; exact conditions make the branch deterministic.

Run this self-contained configuration:

```powershell
$network = @'
{
  "id": "demo-human-decision",
  "name": "Demo - Human decision",
  "mode": "workflow",
  "entry_agents": ["draft"],
  "agents": [
    {"id":"draft","name":"Draft","role":"Propose three checks before releasing a small C utility.","x":0,"y":120},
    {"id":"review","name":"Human reviewer","kind":"human","x":320,"y":120},
    {"id":"accepted","name":"Accepted","role":"Acknowledge approval and list the next release checks.","x":640,"y":0},
    {"id":"rejected","name":"Rejected","role":"Acknowledge rejection and request revised requirements.","x":640,"y":240}
  ],
  "links": [
    {"source":"draft","target":"review","template":"Review this proposal:\n{message}\nReply with exactly APPROVE or REJECT."},
    {"source":"review","target":"accepted","condition":"equals","value":"APPROVE"},
    {"source":"review","target":"rejected","condition":"equals","value":"REJECT"}
  ]
}
'@ | ConvertFrom-Json
$runId = Start-Demo $network 'Propose three checks before releasing a small C utility.'
```

**Show:** Open the run in **Run history**. It remains `waiting` at Human reviewer. Enter exactly `APPROVE` in **Human response**, then click **Send response**. Only Accepted activates. Run the same block again and enter `REJECT`; only Rejected activates.

The comparisons are case-sensitive and include whitespace. Another response matches neither route, so the run can complete without either downstream node. Human input is a response mechanism; approval semantics come from these configured conditions.

**Talking point:** Human-only waiting does not consume active execution time. Use the waiting state to demonstrate **Pause**, **Resume**, or **Cancel** without trying to catch a fast model response. Pause gates future work; an already running model/tool operation may finish.

**Reset:** Finish or cancel the waiting run before starting another presentation attempt.

## 6. Parallel reviews joined before synthesis

**Network:** `brief -> correctness` and `brief -> usability`; both feed `join -> summary`.

```powershell
$network = @'
{
  "id": "demo-parallel-review",
  "name": "Demo - Parallel review",
  "mode": "workflow",
  "entry_agents": ["brief"],
  "limits": {"concurrency":4,"max_calls":12,"max_steps":20},
  "agents": [
    {"id":"brief","name":"Brief","role":"Describe a command-line temperature converter with input validation.","x":0,"y":120},
    {"id":"correctness","name":"Correctness reviewer","role":"Review correctness and boundary cases. Return three concise findings.","x":320,"y":0},
    {"id":"usability","name":"Usability reviewer","role":"Review input messages, output formatting, and user experience. Return three concise findings.","x":320,"y":240},
    {"id":"join","name":"Join reviews","kind":"join","x":640,"y":120},
    {"id":"summary","name":"Summary","role":"Combine both reviews into a prioritized checklist.","x":960,"y":120}
  ],
  "links": [
    {"source":"brief","target":"correctness"},
    {"source":"brief","target":"usability"},
    {"source":"correctness","target":"join"},
    {"source":"usability","target":"join"},
    {"source":"join","target":"summary"}
  ]
}
'@ | ConvertFrom-Json
$runId = Start-Demo $network 'Review a command-line Celsius-to-Fahrenheit converter before release.'
```

**Show:** Both reviewers receive Brief's output. Join combines their results, labeling them `From correctness:` and `From usability:`. Summary activates once, after both arrive. With the demo provider there are five completed node activations and four model calls; Join does not call a model.

**Talking point:** Separate branches can run concurrently subject to network/provider limits. The demo provider is fast, so the timeline is stronger evidence of routing than a speed comparison. A join waits for every incoming predecessor; do not put mutually exclusive approval/rejection branches into this join. A missing predecessor input makes the run fail.

**Reset:** Rerun unchanged, or use a live provider to discuss distinct review content and synthesis.

## 7. A real CLI tool produces JSON and a report artifact

This scenario performs deterministic work without an AI node: Python evaluates a fixed list of temperatures, returns JSON, and writes a report. The tool runs in its own workspace and does not modify repository source files.

Register the demo tool:

```powershell
$tool = @'
{
  "id": "demo-temperature-report",
  "name": "Demo temperature report",
  "kind": "cli",
  "description": "Convert fixed sample temperatures and write a report artifact.",
  "executable": "@python",
  "args": ["-c", "import json; from pathlib import Path; rows = [{'celsius': c, 'fahrenheit': round(c * 9 / 5 + 32, 2)} for c in [-40, 0, 37, 100]]; Path('report.txt').write_text('Temperature conversion report' + chr(10) + chr(10).join(str(r) for r in rows), encoding='utf-8'); print(json.dumps({'rows': rows, 'count': len(rows)}))"],
  "input_schema": {"type":"object","properties":{},"additionalProperties":false},
  "output_format": "json",
  "artifacts": ["report.txt"],
  "timeout": 15
}
'@ | ConvertFrom-Json
Invoke-RestMethod "$base/api/v1/tools/$($tool.id)" `
    -Method Put -Headers $headers -ContentType 'application/json' `
    -Body ($tool | ConvertTo-Json -Depth 20) | Out-Null
```

Run it as an explicit tool node:

```powershell
$network = @'
{
  "id": "demo-cli-artifact",
  "name": "Demo - CLI artifact",
  "entry_agents": ["report"],
  "agents": [
    {"id":"report","name":"Generate report","kind":"tool","tool_id":"demo-temperature-report","tool_arguments":{},"x":100,"y":100}
  ],
  "links": []
}
'@ | ConvertFrom-Json
$runId = Start-Demo $network 'Generate the fixed temperature conversion report.'
```

**Show:** One successful tool call, zero model calls, parsed JSON in the tool result's `data`, and a downloadable `report.txt` artifact under the Tools timeline filter. Logs are artifacts too. The sample results are:

| Celsius | Fahrenheit |
| --- | --- |
| -40 | -40 |
| 0 | 32 |
| 37 | 98.6 |
| 100 | 212 |

**Talking point:** Explicit tool nodes guarantee execution without depending on a model choosing a tool. `@python` selects the backend interpreter on host or container. Each run gets a separate workspace. The run prompt does not change this tool's fixed sample inputs.

**Reset:** Rerun the network; the tool can remain registered for future demos.

## 8. A model-call budget stops a feedback loop

Copy scenario 1's network and allow just one model call:

```powershell
$network = Copy-DemoNetwork 'teacher-student'
$network.id = 'demo-call-budget'
$network.name = 'Demo - One-call budget'
$network.limits.max_calls = 1
$runId = Start-Demo $network 'Explain binary search, then ask the teacher for feedback.'
```

**Show:** Student completes using the one allowed call. Teacher starts, but the scheduler stops before its model request. Final status is `limited`, with `Model call limit reached`. There is one `model_call` event, distinct from scenario 1's normal `completed` ending at the visit limit.

**Talking point:** Per-node visit limits and network-wide model-call limits control different things. A tool-capable agent may make several model calls within one activation. Model-call limits are counts, not currency budgets.

**Recovery:** Change `$network.limits.max_calls = 10` and call `Start-Demo` again with the same prompt. The new run should finish the two-round loop; the limited run remains available for comparison.

## Evidence and troubleshooting

After any scenario, inspect the status and event counts without opening the UI:

```powershell
Invoke-RestMethod "$base/api/v1/runs/$runId" | Select-Object id, status, error
Get-DemoEvents $runId | Group-Object kind | Sort-Object Name | Select-Object Name, Count
```

In **Activity**, use **Export run** to download JSON, CSV, or HTML. JSON includes the initial configuration snapshot and transcript. Inspect the timeline for events and **Use evolved network** for graph changes. XLSX requires the optional Excel dependencies. Save one successful workflow, one human-decision run, one autonomous run, and the limited run to compare execution behavior.

| Symptom | Check/action |
| --- | --- |
| Connection refused or an unexpected 404 | Confirm the Studio process and port. This inspected instance uses 8876; the default/Compose port is 8765. |
| API write returns 403 | Fetch a fresh `/api/v1/session` token and rebuild `$headers`, especially after restarting Studio. |
| `This data directory is already open` | Use the running server, or select another `--data` directory for a separate CLI/server process. |
| C analyzer fails | `cppcheck` is missing on the inspected host. Use scenario 3's compiler-only copy or prepare cppcheck before the demo. |
| A run says `completed` but a tool failed | Inspect `tool_completed.result.ok` and `tool_failure`. Restart an older Studio process to load current mandatory-tool failure handling. |
| AI ignores the specific task | The demo provider is scripted. Select a configured HTTP provider and served model for every relevant AI node. |
| Human decision activates no branch | Enter exactly `APPROVE` or `REJECT`, with no extra spaces or newlines. |
| Parallel review fails with missing join input | Ensure both reviewer links are unconditional and both reviewers deliver to Join. |
| Autonomous run does not delegate on a live model | Verify tool calling, autonomous mode, and Coordinator's orchestration permission; inspect its tool calls and errors. |
| API-created networks/runs do not appear | Refresh Studio and open Run history or the scenario's saved network. |

Run histories and artifacts remain in the Studio data directory. Scenario copies use `demo-*` IDs, and scenario 7 adds only `demo-temperature-report` to the tool registry. Keep these for repeat presentations; remove individual demo configurations through Studio when no longer needed.
