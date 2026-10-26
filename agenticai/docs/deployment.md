# Deployment and installation management

## Standalone

Install the wheel into an isolated Python 3.11+ environment and launch `agenticai serve --open`. The wheel contains the compiled interface and browser tutorial. Choose a data directory with `--data` and an available port with `--port`. Use one server worker.

Model servers are external. The standalone app connects to host or remote HTTP endpoints. GCC and cppcheck must be installed separately for the C tools. Optional Excel export requires `pip install "agenticai-studio[excel]"`. Embedded vLLM is not a default dependency.

## Docker

```text
docker compose up --build -d
```

Open `http://127.0.0.1:8765`. Compose publishes only on loopback and persists `/data` in the `studio-data` volume. If the host port is occupied, change the left-hand port, such as `127.0.0.1:8877:8765`. No host Docker socket is mounted.

Inside the container, `localhost` means the container itself. To reach a model on the host, use `http://host.docker.internal:11434/v1/chat/completions`. For a remote server use its reachable hostname. Pass credential variables through Compose or a local `.env` file; never add secrets to images or exported configurations.

GCC, cppcheck, Bash, Node.js, and npm are available in the image. The entrypoint starts a root APT helper over a local Unix socket, then starts the application as UID/GID 1000. Agent tools and shells run as UID 1000. The root helper accepts validated Debian package identifiers and install/remove operations only. Host file mounts still need permissions suitable for UID 1000.

For deliberate host-file access, add a bind mount and configure the tool working directory to the container path. A Windows executable cannot run in the Linux image; register its Linux equivalent. Host-installed tools do not automatically appear in Docker.

## Tool installations

The installation screen first builds a command preview. Its confirmation fingerprint changes if the package, source, version, action, or recipe changes. Only the reviewed preview can be submitted. Jobs are serialized and retain status, stdout, stderr, exit code, and resolved versions where available. A failed operation does not enter the installed-tool manifest.

Supported managers:

| Manager | Location | Behavior |
|---|---|---|
| pip | Both | Isolated environment under `/data/tools/python` or the standalone data directory |
| npm | Both, when Node/npm available | Dedicated global prefix under `tools/npm` |
| WinGet | Windows standalone | Exact package ID, user scope, no implicit agreement acceptance |
| apt | Docker helper | Debian packages inside the current container |
| recipe | Both | User-defined executable and argument arrays |

Installers may run package-provided setup code. WinGet jobs requiring agreements, interactive setup, or elevation fail with logs rather than silently accepting them. Complete those steps outside the app and check tool availability again. Other package managers use their normal package-installation behavior. This is not a universal automated installer for every operating system or license workflow.

The app does not automatically install software at startup. Review interrupted jobs before retrying. A partially executed installer may have made changes even if the job is interrupted.

## Reproducing tools after container recreation

Managed Python/npm environments persist with the data volume. APT changes live in the current container's writable layer and do not survive creating a new container. Export the tool manifest and image recipe from the installation screen. Build a derived image to preserve system packages:

```text
docker build -t my-agenticai-tools -f Dockerfile.tools .
```

The generated recipe starts from `agenticai-studio:latest` and installs the recorded APT packages. Available resolved versions are pinned. Repositories may eventually remove old versions; retain an image or use your own package mirror for long-term reproducibility. The restore-preview API accepts a version-1 manifest and produces reviewable installation plans for the current environment. Custom recipes must exist before restoring their packages.

## Storage and lifecycle

Use `docker compose down` to stop without deleting the volume. `docker compose down -v` also deletes application data and should be used only when that deletion is intended. Back up the volume or standalone data directory with the application stopped. Do not run two instances against the same SQLite database.

To expose a different hostname deliberately, configure `AGENTICAI_ALLOWED_HOSTS`. `Start-Studio.cmd -External` configures all-interface binding, allows the computer's names/IP addresses, and generates a persistent remote login in `.agenticai/remote-access.json`. Run `Open-Studio-Port.ps1` as administrator to allow inbound TCP 8876. Localhost requests remain available without the remote login. `-LocalOnly` disables remote mode after restarting the server. This setting is remembered between launcher runs.

For other launch methods, set `AGENTICAI_REMOTE_PASSWORD` and optionally `AGENTICAI_REMOTE_USER` (default `studio`) before starting the server. Clients must then authenticate with HTTP Basic, including requests for the session token and tool APIs. Only requests from a loopback peer using a localhost or loopback URL bypass this login; Docker Desktop relays using the external hostname still require it. Host validation and the mutation session token remain enforced after login. HTTP Basic does not encrypt traffic; use an HTTPS reverse proxy when encrypted remote access is required. This remains a single-user application without separate shared-user permissions.

## Building a release

```text
cd frontend
npm ci
npm run build
cd ..
python scripts/build_tutorial.py
python -m build --wheel
```

The tutorial builder copies locally installed reveal.js assets. Screenshots are captured from the real application with `scripts/browser_verify.py`. Run that script after interface changes, then rebuild the tutorial and wheel. The pre-existing cloud-backed `LICENSE` file could not be read during this implementation and is not silently replaced; packaging disables automatic license-file inclusion until that file is available for review.
