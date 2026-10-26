# Copilot Instructions for agenticAI

## Project Overview
- This project orchestrates conversations between two or several AI models, each running on a separate server, to observe their interactions over time.
- The main entry point is typically `main.py`, `main_agentc.py`, `mainT.py`, `main2.py`, `mainR.py`, which instantiate conversation agents and manage the dialogue loop. The starting point depends on the models that are used and which agents are instantiated. The most typical is `main_agentc.py`.
- Each agent is represented by a class (e.g., `agent.py`, `agentC.py`, `agentCompiler.py`, `agentStaticAnalyzer.py`) that encapsulates the logic for interacting with a specific AI model.
- Conversations are initiated with a prompt passed as a command-line argument (`--prompt "Your prompt here"`).
- Logs and results are saved in the `results/` directory.
- The core logic for agent behavior is implemented in files like `agent.py`, `agentC.py`, `agentCompiler.py`, and `agentStaticAnalyzer.py`.

## Key Components
- **Agent Classes**: Each agent class encapsulates the logic for interacting with a specific AI model. Example: `agent.py` and `agentC.py`.
- **Main Scripts**: Scripts such as `main.py`, `main_agentc.py`, and variants (`mainR.py`, `mainT.py`, etc.) set up the agents and start the conversation loop.
- **Requirements**: The `requirements/` directory contains supporting modules (e.g., `agent_3gpp.py`, `agent_reqs.py`) for domain-specific logic.
- **Results**: The `results/` directory stores conversation logs and analysis outputs, often in `.html` or `.xlsx` format.

## Developer Workflows
- **Running a Conversation**: Execute `main.py` or `main_agentc.py` with the `--prompt` argument to start a session. Example:
  ```bash
  python main_agentc.py --prompt "Discuss the architecture of agenticAI."
  ```
- **Debugging**: Logs are written to `debug_log.txt` and may also be output to the console.
- **Analysis**: Use the provided Jupyter notebooks (e.g., `analyze.ipynb`) or scripts like `convert_to_html.py` to process and visualize results.

## Project Conventions
- **Agent Instantiation**: Always instantiate agents via the main script; do not create agent instances directly in utility modules.
- **Result Files**: Output files are named to reflect the models and session (e.g., `analyze_llama32_llama32.html`).
- **Extensibility**: To add a new agent/model, create a new agent class (e.g., `agentNewModel.py`) and update the main script to use it.
- **No Central Config**: Most configuration is done via script arguments or by editing the main script directly.

## Integration Points
- **External Models**: Agents communicate with external AI model servers; connection details are typically hardcoded or passed as arguments.
- **Requirements Modules**: Domain-specific logic is factored into the `requirements/` directory for reuse.

## Examples
- To run a conversation and save results:
  ```bash
  python main_agentc.py --prompt "Explain 3GPP standards."
  # Output will be saved in results/ as an .html or .xlsx file
  ```
- To analyze results:
  Open `analyze.ipynb` or run `convert_to_html.py` on a results file.

## Key Files/Directories
- `main.py`, `main_agentc.py`: Entry points for running conversations
- `agent.py`, `agentC.py`, `agentCompiler.py`, `agentStaticAnalyzer.py`: Core agent logic
- `requirements/`: Domain-specific modules
- `results/`: Output logs and analysis
- `analyze.ipynb`, `convert_to_html.py`: Analysis tools

---
For more details, see `README.md` or review the main scripts for usage patterns.
