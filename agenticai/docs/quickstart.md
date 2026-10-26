# Getting started

## Standalone Python application

Use Python 3.11 or newer. A prebuilt wheel contains the web interface and tutorial.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .\dist\agenticai_studio-1.0.0-py3-none-any.whl
.\.venv\Scripts\agenticai.exe serve --open
```

Open `http://127.0.0.1:8765`. The default data directory is `~/.agenticai`. Use `--data PATH` to choose another directory and `--port 8876` if the default port is occupied. On Linux/macOS use `.venv/bin/agenticai`. Node.js is needed only for frontend development or npm-based tools.

For development from this source directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,excel]"
cd frontend
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe -m agenticai serve --open
```

## First network

1. Open the default **Programmer & designer** example. The demo provider requires no credentials.
2. Select **Start** and enter the **Initial task**. It is saved with the network and included in its JSON export.
3. Connect Start to the first recipient, or use its recipient checkboxes. This example starts with Programmer, then sends code to Designer for review and feedback.
4. Select an agent to edit its instructions, model, parameters, visit limit, and tools. Select a communication link to edit its template or condition.
5. Save and choose **Run network**. The task field below the canvas edits the same saved initial task.
6. Follow the Activity timeline. Export the conversation as JSON, CSV, HTML, or Excel.

The example uses three visits per agent. Repeated visits terminate when that agent's configured visit limit is reached. Adjust run limits with the settings button beside the execution mode. Teacher & student remains available as another example.

## Real model servers

Open **Model providers**, add a provider, and enter its complete compatible chat-completion endpoint, such as `http://localhost:11434/v1/chat/completions`. Enter the model name served by that endpoint. Use the connection test or model discovery. The model name is not inferred from the URL.

For an authenticated server, set the credential environment variable before starting the backend:

```powershell
$env:OPENAI_API_KEY = "your-key"
agenticai serve
```

Store only `OPENAI_API_KEY` in the provider's credential field. Choose the provider and model for each agent. Enable tool calling only when the server and selected model support it. The deterministic demo is for verifying orchestration and UI behavior, not evaluating reasoning quality.

## Autonomous collaboration

Select **Autonomous team** and run a task. The demo coordinator creates a child, delegates the task, and receives its result. Inspect network-change events, then choose **Use evolved network** to load a new editable copy. Save it to keep it.

For real models, enable orchestration on the appropriate agents. A child may receive only a subset of its parent's tools. Communication requires links; agents with orchestration may add their own outgoing links. Limits cover children and all model calls.

## CLI tools

Open **Tools & CLI**, register a tool, and choose its executable, argument templates, schema, stdin, and output behavior. Test it, then select an agent and enable the tool. See the tool guide for complete examples. **Install & manage** previews package-manager commands and runs them only after confirmation. It supports pip, npm, WinGet, Docker APT, and custom recipes.

## Command line

```text
agenticai validate network.json
agenticai run network.json --data ./run-data
agenticai run network.json --prompt "Explain the task" --data ./run-data
agenticai run network.json --prompt "Explain the task" --providers providers.json --tools tools.json
```

Omit `--prompt` to use the network's saved initial task, or supply it for a run-specific task. Provider/tool files contain JSON arrays using the same definitions as the API. The runner prompts on stdin for human nodes and exits nonzero for failed, cancelled, or limited runs. Use a separate data directory when the web server is already using the default one.

## Tutorial

Open **Getting started** in the sidebar, or `/tutorial/`. Use arrow keys or Space, `F` for fullscreen, `O` for overview, and `S` for presenter notes. Open `/tutorial/?print-pdf` to print the slides. All slide assets are local.
