# AgenticAI Studio

A local visual workspace for configuring agents, connecting networks, and inspecting every conversation and tool call. Supports directed workflows and autonomous collaboration, including delegation, dynamic agents, topics, CLI tools, scripts, shell access, and Python plugins.

## Run the standalone application

On Windows, double-click **Start-Studio.cmd** in this project to start or reopen Studio at [http://127.0.0.1:8876](http://127.0.0.1:8876). The launcher runs the server in the background, waits until it is ready, and opens your browser. It preserves the existing workspace data. Reopen it after restarting Windows; refreshing a browser tab alone does not start the local server. Startup logs are saved under `.build/studio-launcher`.

For remote access, run `Start-Studio.cmd -External`. This binds port 8876 on all interfaces and remembers that setting for subsequent launches. Remote visitors must log in; credentials are generated in `.agenticai/remote-access.json`. Loopback access continues to work without that login. Run `Open-Studio-Port.ps1` as administrator once to allow inbound TCP 8876, matching the SDV and 5G firewall rules. Use `Start-Studio.cmd -LocalOnly` to switch back. Stop the running Studio process before changing its binding. The launcher prints the machine's current IP addresses; opening the firewall does not configure upstream routers or DNS.

Python 3.11 or newer is required. The release wheel includes the compiled web interface and offline browser presentation.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .\dist\agenticai_studio-1.0.0-py3-none-any.whl
.\.venv\Scripts\agenticai.exe serve --open
```

Open [the local interface](http://127.0.0.1:8765). Use `--port 8876` if the port is occupied, or `--data PATH` for separate storage. Linux/macOS use `.venv/bin/agenticai`. No Node.js installation is needed to run the compiled UI; npm tools require Node/npm.

The default example is **Programmer & designer**, using a deterministic demo provider with no model server or credentials required. Select **Start** to enter the initial task and choose its first recipients. Programmer receives the task first; Designer reviews its code and sends feedback for up to three rounds. The task is saved and exported with the network. Select an agent to configure its role, provider, model parameters, tools, and communication permissions. Select a link to edit its message template and condition.

## Docker

```text
docker compose up --build -d
```

The image includes GCC, cppcheck, Bash, Node.js, and npm. Compose binds to loopback and persists application data in a named volume. Use `host.docker.internal` to reach a model server on the host. Agent execution is unprivileged; a restricted local helper handles explicit system-package installation requests.

## CLI tools and installation

Register any available executable or script under **Tools & CLI**. Define argument templates, a JSON input schema, stdin, environment references, timeouts, accepted exit codes, output format, and artifact patterns. Test the registration, then enable it for individual agents. Shell access is optional and executes with the app account's permissions.

The installation screen previews and manages pip, npm, WinGet, Docker APT, and custom recipe jobs. Managed Python/npm environments persist in the data directory. Export a manifest or a derived-image recipe to reproduce tools elsewhere.

## Model servers and credentials

Add compatible HTTP chat-completion endpoints under **Model providers**. Configure the model served by each endpoint. Tool calling requires support from both server and model. API keys are environment-variable references, never browser configuration values.

```powershell
$env:OPENAI_API_KEY = "your-key"
agenticai serve
```

## Command-line networks

```text
agenticai validate agenticai/examples/teacher-student.json
agenticai run agenticai/examples/teacher-student.json --prompt "Solve the task" --data ./demo-data
```

Existing `main.py`, `main_agentc.py`, and related scripts retain their synchronous core-agent interfaces. Install `.[legacy]` for their tqdm/Excel dependencies. Compiler/analyzer adapters now use isolated files, check return codes, and recheck applied repairs. Excel-only dependencies are optional: install `.[excel]` when working from source.

## Documentation and presentation

- [Quickstart](agenticai/docs/quickstart.md)
- [Architecture](agenticai/docs/architecture.md)
- [CLI tools and Python plugins](agenticai/docs/tools.md)
- [Deployment and installation](agenticai/docs/deployment.md)
- [API contracts](agenticai/docs/api.md)
- [Performance analysis and measured results](agenticai/docs/performance.md)

The app serves an [18-slide tutorial](http://127.0.0.1:8765/tutorial/) with actual screenshots, speaker notes, and printable slides. OpenAPI is at `/docs`.

## Development and verification

```text
python -m pip install -e ".[dev,excel,benchmark]"
cd frontend
npm ci
npm run build
cd ..
python -m pytest tests -q
python scripts/benchmark.py
python scripts/build_tutorial.py
python -m build
```

`scripts/browser_verify.py` exercises the production UI and captures tutorial screenshots. `scripts/verify_container.py` tests the container's workflow, CLI execution, installation, and persistence.

Some original files, including the old tests, dependency list, domain agents, and LICENSE, remain unavailable cloud placeholders in this workspace. Their content has not been overwritten or claimed as verified. The new test suite lives in `tests/`; `scripts/inspect_cloud_files.py` records bounded attempts to read the legacy files.
