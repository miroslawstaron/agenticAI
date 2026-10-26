"""Build the offline browser presentation using actual UI captures and reveal.js."""

import html
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "agenticai/static/tutorial"
vendor = root / "frontend/node_modules/reveal.js"
target.mkdir(parents=True, exist_ok=True)
for name in ["dist/reveal.css", "dist/reveal.js", "plugin/notes/notes.js", "LICENSE"]:
    dest = target / "vendor" / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(vendor / name, dest)

slides = [
    (
        "AgenticAI Studio",
        "A hands-on guide to configuring and running agent networks.",
        None,
        [
            "Local Python application and Docker deployment",
            "Visual workflows and autonomous collaboration",
            "CLI tools, scripts, and Python plugins",
        ],
        "This tutorial follows the actual shipped interface. Start with the deterministic demo before connecting a real inference server. The application is single-user and binds to loopback by default. Source: quickstart.md.",
    ),
    (
        "Installation",
        "The Python wheel includes the web interface and this tutorial.",
        None,
        [
            "python -m pip install agenticai_studio-1.0.0-py3-none-any.whl",
            "agenticai serve --open",
            "Docker: docker compose up --build -d",
        ],
        "Install the supplied wheel from its local path; the command shown is a filename, not a promise of a public package registry release. Python 3.11+ is required. The default address is http://127.0.0.1:8765. Use --port when occupied and --data to select storage. Source: deployment.md.",
    ),
    (
        "The workspace",
        "A saved network contains agents, communication links, and execution limits.",
        "workspace",
        [
            "Choose a network in the sidebar.",
            "Select a node to inspect it.",
            "Save changes before leaving the network.",
        ],
        "The teacher/student demo ships with two visits per agent. Drag nodes to arrange the graph. More nodes adds human input, explicit tool steps, and joins. Source: quickstart.md.",
    ),
    (
        "Model providers",
        "Each agent can connect to its own compatible HTTP model server.",
        "provider-settings",
        [
            "Enter the complete chat-completion endpoint.",
            "Reference an environment variable for credentials.",
            "Test with a model actually served by the endpoint.",
        ],
        "Model discovery is optional. Manual model names are supported. In Docker, use host.docker.internal to reach a host model server. Enable tool calling only when both model and server support it. The test reports whether the probe tool was actually called. Source: architecture.md and deployment.md.",
    ),
    (
        "Agent instructions",
        "The system prompt defines the agent’s role in the task.",
        "agent-settings",
        [
            "Give the agent a clear responsibility.",
            "Choose its provider and model.",
            "Mark entry agents to receive the initial task.",
        ],
        "Agent library saves reusable node definitions. Duplicating a network preserves the setup while assigning a new network ID. Different agents may use different providers and models. Source: quickstart.md.",
    ),
    (
        "Model parameters and budgets",
        "Control response length, retained context, and repeated activations.",
        "agent-inspector",
        [
            "Temperature affects sampling.",
            "Output tokens reserve response capacity.",
            "Maximum visits bounds feedback loops.",
        ],
        "The context policy uses conservative UTF-8 bytes, not a provider tokenizer. It retains full turns and matched tool exchanges. The original transcript remains in SQLite. Use run limits to control total agents, calls, concurrency, steps, and active time. Source: architecture.md.",
    ),
    (
        "Communication links",
        "A link determines where output goes and how the next input is formed.",
        "communication",
        [
            "{message} inserts the preceding response.",
            "Conditions select matching output.",
            "Connections also define autonomous message destinations.",
        ],
        "Drag a right handle onto a left handle to create a link. Select a link to change its template and condition. Autonomous orchestrators may add outgoing links during a run; such changes do not overwrite the saved network. Source: architecture.md.",
    ),
    (
        "Parallel workflows",
        "Independent branches run concurrently under configured limits.",
        "parallel-workflow",
        [
            "Tool steps accept mapped incoming text.",
            "A join waits for every incoming predecessor.",
            "Cycles stop at visit or run limits.",
        ],
        "The C verification example generates a program, then compiles and analyzes it in separate workspaces. GCC checks compilation; cppcheck reports findings. Generated programs are not run automatically. Conditional branches feeding a join must all deliver. Source: architecture.md and tools.md.",
    ),
    (
        "The tool registry",
        "Register an executable once, then enable it for selected agents.",
        "tool-registry",
        [
            "CLI tools need no Python adapter.",
            "Compiler and analyzer tools are built in.",
            "Shell access is enabled separately.",
        ],
        "The registry stores tool definitions, not credentials. Agents see only the tools enabled on their own configuration. Child agents can inherit a subset of their parent’s tools. Source: tools.md.",
    ),
    (
        "CLI registration",
        "Arguments are passed as individual values to the executable.",
        "cli-editor",
        [
            "Each line is one argument.",
            "${name} substitutes a validated input.",
            "Set stdin, environment references, and artifacts.",
        ],
        "Use an absolute executable path or a command on PATH. @python selects the app interpreter. Scripts require an explicit interpreter. Registered direct-executable argument values are not implicitly interpreted by a shell. For Node CLI .cmd shims on Windows, prefer node plus the JavaScript entry script. Source: tools.md.",
    ),
    (
        "Tool testing",
        "Check the result before granting the capability to an agent.",
        "cli-test",
        [
            "Provide an input object matching the schema.",
            "Inspect stdout, stderr, and exit status.",
            "Download logs and generated files.",
        ],
        "JSON output mode parses stdout into structured data. Oversized or invalid JSON fails clearly. Accepted exit codes default to zero. Tool logs are bounded and secrets are redacted. Test executions use separate workspaces. Source: tools.md.",
    ),
    (
        "Installing tools",
        "Review the exact package-manager command before it runs.",
        "install-preview",
        [
            "Select pip, npm, WinGet, APT, or a recipe.",
            "Choose the package and optional version.",
            "Confirm the preview and inspect the job log.",
        ],
        "The installation screen is user initiated and is not exposed as a model tool. WinGet agreement and elevation requirements are not silently accepted. Managed Python/npm environments persist with application data. APT additions require a derived image or explicit restoration after container recreation. Source: deployment.md.",
    ),
    (
        "Shell access",
        "A shell-enabled agent can use pipelines and command sequences.",
        "shell-settings",
        [
            "PowerShell on Windows; Bash in Docker.",
            "Commands run with application-account permissions.",
            "Timeouts and cancellation terminate process trees.",
        ],
        "Shell access is powerful and intentional. It is not a sandbox between agents. A standalone shell can access host files available to the account. Container commands execute as UID 1000 and can access mounted files. Interactive terminal applications are outside this runner. Source: tools.md and architecture.md.",
    ),
    (
        "Autonomous collaboration",
        "An orchestrator can create an agent, delegate work, and change its connections.",
        "autonomous-network",
        [
            "Children inherit a permitted tool subset.",
            "Delegated results return asynchronously.",
            "Save an evolved graph explicitly to reuse it.",
        ],
        "The demo coordinator uses deterministic native tool calls to spawn a child and delegate work. Real models must support tool calling. Limits include dynamically created agents. Topic publication reaches connected subscribers. Source: architecture.md.",
    ),
    (
        "Human input",
        "A human node pauses its branch until you respond.",
        "human-review",
        [
            "Read the incoming task in Activity.",
            "Enter a response and send it.",
            "Execution continues with the response as output.",
        ],
        "Waiting time is excluded when all remaining activations are waiting for humans. The command-line runner prompts on stdin. Restarting the application marks unfinished runs interrupted rather than replaying tool side effects. Source: architecture.md and quickstart.md.",
    ),
    (
        "Run monitoring",
        "The timeline records conversations, tool results, and network changes.",
        "run-activity",
        [
            "Inspect model latency and available token usage.",
            "Pause between steps or cancel execution.",
            "Open artifacts from completed tool calls.",
        ],
        "Pause does not undo in-flight work. Cancellation terminates local subprocess trees and outstanding local HTTP waits; external inference may already be executing. Token totals are shown only when providers report them. Source: api.md and architecture.md.",
    ),
    (
        "History and exports",
        "Saved runs retain the configuration used for execution.",
        "run-history",
        [
            "Reopen any run from history.",
            "Export JSON, CSV, HTML, or optional Excel.",
            "Preserve the data directory or Docker volume.",
        ],
        "Excel support is an optional extra. Full transcript storage is incremental; exports are generated only when requested. HTML is escaped and formula-like spreadsheet cells are neutralized. Use stopped-server backups or SQLite’s backup mechanism. Source: deployment.md and api.md.",
    ),
    (
        "Architecture and next steps",
        "The local reference library explains runtime behavior and extension points.",
        "documentation",
        [
            "Read the architecture and tool guides.",
            "Explore the OpenAPI reference at /docs.",
            "Connect a real provider and adapt a demo network.",
        ],
        "The performance report contains reproducible fixture measurements and their limits. Original cloud-backed files could not all be inspected. Model inference quality and real endpoint throughput must be evaluated separately. All tutorial screenshots are captures of the running application. Sources: performance.md, api.md, architecture.md.",
    ),
]
assert len(slides) == 18
parts = []
for index, (title, subtitle, image, bullets, notes) in enumerate(slides):
    if image and not (target / "images" / (image + ".png")).is_file():
        raise FileNotFoundError(
            f"Missing real screenshot: {image}; run scripts/browser_verify.py first"
        )
    image_html = (
        f'<figure><img src="images/{image}.png" alt="{html.escape(title)} in AgenticAI Studio"></figure>'
        if image
        else ""
    )
    cls = "illustrated" if image else ("cover" if index == 0 else "text-slide")
    body = "".join("<li>" + html.escape(text) + "</li>" for text in bullets)
    parts.append(
        f'<section class="{cls}"><div class="slide-content"><div class="copy"><p class="chapter">AGENTICAI STUDIO · USER GUIDE</p><h1>{html.escape(title)}</h1><p class="subtitle">{html.escape(subtitle)}</p><ul>{body}</ul></div>{image_html}</div><aside class="notes">{html.escape(notes)}</aside></section>'
    )
document = (
    """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AgenticAI Studio — Usage presentation</title><link rel="stylesheet" href="vendor/dist/reveal.css"><link rel="stylesheet" href="tutorial.css"></head><body><a class="home" href="/">← Studio</a><div class="reveal"><div class="slides">"""
    + "".join(parts)
    + """</div></div><script src="vendor/dist/reveal.js"></script><script src="vendor/plugin/notes/notes.js"></script><script>Reveal.initialize({width:1440,height:810,margin:0,hash:true,slideNumber:'c/t',transition:'none',backgroundTransition:'none',center:false,plugins:[RevealNotes],pdfSeparateFragments:false});</script></body></html>"""
)
(target / "index.html").write_text(document, encoding="utf-8")
(target / "slides.json").write_text(
    json.dumps(
        [{"number": i + 1, "title": s[0], "notes": s[4]} for i, s in enumerate(slides)],
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)
(target / "tutorial.css").write_text(
    """html,body{background:#f4f6f2;color:#243e35;font-family:"Segoe UI",Arial,sans-serif}*{box-sizing:border-box}.reveal{font-family:inherit;color:#243e35}.reveal .slides{text-align:left}.reveal .slides>section{height:810px;padding:0}.slide-content{display:flex;height:100%;align-items:center;padding:70px 65px;gap:48px}.copy{flex:0 0 440px;min-width:0}.chapter{font-size:12px;letter-spacing:3px;color:#7b9d8a;margin:0 0 28px;font-weight:600}.reveal h1{font-size:44px;line-height:1.12;font-weight:600;letter-spacing:-1.5px;margin:0 0 23px;color:#244e3f}.subtitle{font-size:25px;line-height:1.5;font-weight:400;color:#718a7d;margin:0 0 36px}.reveal ul{display:block;font-size:22px;line-height:1.65;padding-left:22px;margin:0;color:#536f60}.reveal li{margin-bottom:18px;padding-left:4px}.reveal figure{flex:1;min-width:0;margin:0}.reveal figure img{max-width:100%;max-height:650px;object-fit:contain;margin:0;box-shadow:0 14px 45px #23473816;border:1px solid #d6e2d7;border-radius:4px}.reveal .cover{background:#122f27}.cover .slide-content{padding:100px 115px}.cover .copy,.text-slide .copy{flex:1;max-width:1150px}.reveal .cover h1{font-size:92px;letter-spacing:-4px;color:#d2f2de;margin-bottom:30px}.cover .chapter{color:#7da58d}.cover .subtitle{font-size:34px;color:#9fc6ae;max-width:950px;margin-bottom:55px}.cover ul{color:#b6d8c2;font-size:26px;line-height:1.8}.text-slide .slide-content{padding:80px 115px}.text-slide h1{font-size:64px}.text-slide .subtitle{max-width:950px;font-size:30px}.text-slide ul{font:24px/2 Consolas,monospace}.home{position:fixed;left:22px;top:20px;z-index:10;font-size:12px;color:#81a18d;text-decoration:none}.reveal .progress{color:#3b8b67;height:3px}.reveal .controls{color:#3c8967}.reveal .slide-number{background:transparent;color:#7b9b88;font:13px "Segoe UI",sans-serif;right:25px;bottom:20px}.reveal .speaker-notes{font-family:"Segoe UI",sans-serif}@media print{.home{display:none}.reveal figure img{box-shadow:none}}""",
    encoding="utf-8",
)
print(f"Built {len(slides)} local slides in {target}")
with (target / "tutorial.css").open("a", encoding="utf-8") as css:
    css.write(
        "\n.reveal figure{display:flex;justify-content:center}.reveal ul{font-size:23px}.reveal .cover ul{font-size:26px}\n"
    )
