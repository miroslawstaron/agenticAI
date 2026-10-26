# Framework analysis and performance

## Findings and changes

| Priority | Original behavior | Change and effect |
|---|---|---|
| High | Compiler/analyzer calls shared `temp/code_temp.c` and `a.out` | Unique invocation directories prevent concurrent runs from overwriting files |
| High | Static analyzer requested a repair but did not apply or recheck it | Legacy adapter now applies each repair and reruns compilation/analysis |
| High | Success inferred from the word `error` in stderr | Check process return codes and cppcheck's explicit error-exit status |
| High | Subprocesses lacked timeouts and cancellation | Bound runtime and terminate descendant processes |
| High | HTTP failure could return `None` into later prompts | Explicit runtime errors and consistent legacy failure behavior |
| Medium | Top-level `requests.post` created new connections | Reuse pooled HTTPX clients |
| Medium | Every independent branch ran sequentially | Concurrent independent activations with global and endpoint limits |
| Medium | Complete growing conversations were sent on every call | Drop whole old turns under a bounded request-context policy |
| Medium | Excel files were rewritten after every loop iteration | Commit SQLite messages/events incrementally; export on demand |
| Medium | Model parameters and API-key behavior differed across agent classes | Central models, transport, credential references, and compatibility adapters |
| Medium | Exported HTML inserted model text directly | Escape HTML; neutralize spreadsheet formula prefixes |
| Low | Multiple scripts hard-coded endpoints and conversation loops | Versioned reusable configurations and a visual editor |

The readable embedded-vLLM module also creates a model instance per agent and contains unresolved function/name references. It remains a legacy GPU path outside this HTTP-first release. Use a shared vLLM server for the new runtime. Domain and human legacy sources/tests were unavailable as cloud placeholders during inspection; no full regression claim is made for those modules.

## Measured results

The reproducible benchmark is `scripts/benchmark.py`; raw output is `benchmark-results.json`. Run it with Python plus requests, pandas, and openpyxl installed. It uses a loopback HTTP/1.1 fixture with a 30 ms response delay, twenty batches, and four independent agents per batch.

| Measurement | Legacy pattern | Improved pattern |
|---|---:|---:|
| Median four-request batch | 138.000 ms | 63.083 ms |
| p95 batch | 184.294 ms | 65.871 ms |
| Requests per second | 27.63 | 63.99 |
| Connections observed over 80 requests | 80 | 4 |
| Peak traced Python allocations | 560.9 KiB | 1,019.8 KiB |
| Request context after 100 turns | 67,931 bytes | 5,473 bytes |
| Persisting 60 successive messages | 1,261.52 ms, repeated Excel | 108.48 ms, incremental SQLite |

The independent-batch median improved by **2.19×**. Incremental persistence improved by **11.63×** in this fixture. These figures were measured on Windows 11 with Python 3.14.7. A prior run measured 2.92× and 11.16× respectively; timing varies with system load. The table and raw JSON show the final run. The asynchronous implementation used more traced Python allocation during the parallel workload. It is not presented as a memory reduction.

The request-context comparison retains the complete archive and bounds only the portion submitted to the model. Completed runtime objects are released; run history remains in SQLite. There is no claim that total archive storage stops growing.

## Interpretation

These are synthetic framework measurements, not measurements of model reasoning quality or real GPU inference. Dependent teacher/student turns still execute sequentially. Actual throughput depends on model-server capacity, request length, rate limits, and endpoint concurrency. On-demand Excel export still has a cost; it is moved out of the conversation loop.

Connection pooling is useful for repeated calls. Increasing concurrency beyond server capacity can increase latency and failures. Begin with the default per-endpoint limit of two, measure your actual endpoint, and tune from observed throughput and latency. Token usage is displayed only when reported by the provider; the context policy is a conservative byte estimate rather than an exact tokenizer.

## Reproduction

```text
python scripts/benchmark.py --rounds 20 --output agenticai/docs/benchmark-results.json
python -m pytest tests -q
python scripts/browser_verify.py --url http://127.0.0.1:8876
```

Use a deterministic fixture for regression testing and a separately configured real endpoint for inference measurements. Do not infer real-model speedups from the loopback fixture.
