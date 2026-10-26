# Release verification

Verification performed on 23–24 October 2026 against the shipped implementation.

## Automated checks

- **66 tests passed on Windows 11 / Python 3.14.7.**
- **66 tests passed on Linux / Python 3.12 in the rebuilt Docker image.**
- **Five frontend session tests passed on Windows and during the Docker build.** These check initial authentication, expired-token recovery, concurrent renewal, rejection without replay, and the one-retry limit.
- Frontend TypeScript checking and production build passed.
- Python lint and formatting checks passed for the new runtime, compatibility adapters, scripts, and tests.
- A clean Python environment installed the release wheel, served its packaged UI/tutorial, executed autonomous delegation, exported a run, and ran the installed CLI workflow.

The tests exercise retries, malformed responses, endpoint concurrency, complete-turn context trimming, literal arguments, stdin/Unicode, environment references, log redaction, artifact collection, exit codes, timeouts, cancellation, orphan descendants, isolated compilation, native tool calls, workflows, conditions, joins, feedback limits, human waiting, dynamic agents, delegation, capability inheritance, API session protection, installation jobs, manifests, legacy repair loops, and interruption recovery.

## Browser checks

The production application was exercised in Chromium. Checks covered saving and running a workflow, CLI testing, installation previews, autonomous creation/delegation, saving an evolved graph, human input, and tablet layout. No browser JavaScript errors were reported. Screenshots in the tutorial were captured from that application.

The starting-point regression checks also passed through the external HTTP address with remote login: the default Programmer/Designer selection, recovery from an expired session token, multiline/Unicode task persistence, JSON export/import, deleting and restoring Start connections, and three ordered Programmer/Designer feedback rounds. Edited legacy example configurations survive the built-in upgrade unchanged. Run `scripts/verify_workflow_start.py` to repeat these checks; `--credentials-file` accepts the private remote-access JSON when testing an external address.

All eighteen tutorial slides were rendered and checked for text overflow and missing images. The tutorial requested no external resources. Presenter mode loaded the current-slide preview in a same-origin iframe.

## Container checks

The real Linux image generated C, compiled it with GCC, and analyzed it with cppcheck. A shell pipeline reported UID 1000. User-initiated pip, npm, and APT jobs installed ruff, json5, and jq. Each executable was called through the tool runner. The manifest recorded resolved versions.

The application container was removed and recreated with its data volume and a generated derived-image recipe. Runs, tool definitions, managed Python/npm environments, and pinned APT tools remained usable. Temporary verification containers and volumes were removed; the built application image remains available locally.

## Performance evidence

The final controlled fixture measured 2.19× faster independent-request batches and 11.63× faster incremental persistence than the corresponding legacy patterns. See the performance guide and raw benchmark JSON for workload, variability, allocation tradeoffs, and limits. These are not real-model inference measurements.

## Remaining external verification

Original legacy tests, requirements/domain modules, and LICENSE still could not be read because Windows cloud hydration timed out. The unavailable source files were not overwritten. New replacement tests and readable core-script interfaces were checked, but a complete regression claim against the original unavailable suite is not possible.

No live Ollama, vLLM, or paid model endpoint was exercised. Compatible HTTP behavior and native tool dispatch were verified with controlled fixtures; configure and test your actual endpoint before relying on its model-specific capabilities. WinGet preview/agreement behavior was checked, while actual package installation was exercised through the container's pip/npm/APT managers rather than installing software into the host OS.
