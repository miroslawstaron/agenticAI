# CLI tools, shells, and Python plugins

## Registered executables

A registered CLI tool launches an executable with an argument array. Each configured line is one argument. `${name}` substitutes a validated input value; spaces and shell characters in that value remain part of the argument. JSON braces, ordinary `$` characters, and backticks are not interpolation syntax.

Example: register `git` with arguments `log`, `-n`, `${count}`, `--oneline`, a working directory pointing at a repository, and this schema:

```json
{"type":"object","properties":{"count":{"type":"integer","minimum":1,"maximum":100}},"required":["count"],"additionalProperties":false}
```

The model calls the tool with `{"count":5}`. No Python wrapper is required. Use an absolute executable path if the CLI is not on PATH. `@python` selects the application's Python interpreter. Managed Python/npm tool directories are prepended to the execution PATH.

Example Python script arguments:

```text
-u
C:\tools\analyze.py
--input
${filename}
```

Register the Python interpreter as the executable. For PowerShell scripts, explicitly use `powershell.exe` with `-NoProfile`, `-NonInteractive`, `-File`, the script path, and its arguments. For Bash scripts, use `bash` with the script path. Windows `.cmd`/`.bat` launchers need an explicit interpreter; for Node CLIs prefer `node` and the package's JavaScript entry script to preserve literal argument handling.

## Inputs and outputs

Every tool has a JSON Schema describing its argument object. Input validation happens before a process is started. Set stdin independently with a template, or leave it empty. Map subprocess environment variable names to server environment variable names, for example `{"TOKEN":"MY_SERVICE_TOKEN"}`. Credential values are not stored in tool configuration.

An empty working directory creates an isolated workspace for each invocation. An explicit directory enables deliberate shared-file access. Artifact glob patterns must be relative, without `..`, and remain within that working directory. Shared-directory artifacts are copied into the run workspace for download. Tools are trusted processes and can still write to other OS-accessible locations.

Every result contains `ok`, `stdout`, `stderr`, `exit_code`, `duration`, `timed_out`, `artifacts`, `data`, and `error`. Accepted exit codes default to `[0]`. JSON mode parses the captured stdout into `data`; invalid or truncated JSON produces a clear failure. Stdout/stderr sent back to the model are bounded. Each full log is capped at 16 MiB, redacted, and available as an artifact. Timeouts and cancellation kill the process tree, including descendants still holding output pipes.

The initial runner supports noninteractive commands. Finish authentication and other interactive setup before using a CLI with agents. Tools requiring terminal UI sessions are outside this runner's scope.

## Shell access

Enable the Shell tool for an agent to allow pipelines, redirection, and command sequences. The default is noninteractive PowerShell on Windows and Bash on Linux. Input is `{"command":"..."}`. Shell syntax is interpreted intentionally in this mode. Explicit interpreter tools can also invoke that interpreter's language.

Standalone shells execute as your application account. Container shells execute as UID 1000 inside the container and can access mounted files. Neither is a sandbox between agents. Shell-capable agents can invoke accessible package managers themselves; the app's installation screen is not a restriction on what an unrestricted shell can do.

## Compiler and analyzer

The built-in GCC tool writes extracted C to a unique invocation directory, checks the exit code, and returns diagnostics and artifacts. It never runs the generated program automatically. cppcheck uses `--error-exitcode=1` so findings affect success. Missing GCC/cppcheck produces an actionable tool error. Both are included in Docker.

The legacy `AgentCompiler` and `AgentStaticAnalyzer` adapters retain their constructors and `get_response(code)` interface. They apply every model repair and rerun compilation/analysis. Inspect `last_result` for final success and diagnostics; returned code alone does not imply verification succeeded.

## Python plugin contract

Install a trusted Python package into the application's environment. Declare an entry point:

```toml
[project.entry-points."agenticai.tools"]
word_count = "my_package.word_count"
```

The module exposes optional metadata and an execution function:

```python
metadata = {
    "description": "Count words",
    "input_schema": {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
}


def execute(arguments, workspace):
    return {"words": len(arguments["text"].split())}
```

`execute` may be synchronous or asynchronous and must return JSON-serializable data. The `workspace` argument is a `pathlib.Path`. Keep diagnostic output on stderr; stdout is the JSON result channel. Plugins run in subprocesses so cancellation and timeouts apply. Register a tool of type `python`, set the plugin entry-point name and matching input schema, then test it. `/api/v1/plugins` lists installed entry points and metadata. Restart the server after installing a new plugin package.
