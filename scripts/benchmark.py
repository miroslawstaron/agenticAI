"""Reproducible local HTTP fixture benchmark; no model credentials are used."""

import argparse
import asyncio
import json
import platform
import socket
import statistics
import threading
import time
import tracemalloc
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import psutil

from agenticai.models import Agent, Provider
from agenticai.store import Store
from agenticai.transport import Transport, bounded_messages

connections = set()
payload_bytes = []


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        length = int(self.headers["Content-Length"])
        self.rfile.read(length)
        connections.add(self.client_address)
        payload_bytes.append(length)
        time.sleep(0.03)
        body = json.dumps(
            {
                "choices": [
                    {"message": {"role": "assistant", "content": "fixture response"}}
                ],
                "usage": {"total_tokens": 12},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def stats(samples):
    ordered = sorted(samples)
    return {
        "median_ms": round(statistics.median(samples) * 1000, 3),
        "p95_ms": round(
            ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))] * 1000, 3
        ),
    }


async def benchmark(rounds):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    endpoint = f"http://127.0.0.1:{server.server_port}/v1/chat/completions"
    messages = [
        {"role": "system", "content": "Fixture agent"},
        {"role": "user", "content": "Fixture task"},
    ]
    result = {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "fixture_delay_ms": 30,
            "rounds": rounds,
            "independent_agents": 4,
        },
        "scenarios": {},
    }
    try:
        # Reproduce original requests.post per-call behavior; preserve identical payloads.
        import requests

        baseline = []
        connections.clear()
        tracemalloc.start()
        start = time.perf_counter()
        for _ in range(rounds):
            one = time.perf_counter()
            for _ in range(4):
                response = await asyncio.to_thread(
                    requests.post,
                    endpoint,
                    json={
                        "model": "fixture",
                        "messages": messages,
                        "temperature": 0.5,
                        "max_tokens": 128,
                        "stream": False,
                    },
                    timeout=5,
                )
                response.raise_for_status()
            baseline.append(time.perf_counter() - one)
        baseline_total = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        result["scenarios"]["legacy_sequential"] = {
            **stats(baseline),
            "connections": len(connections),
            "requests_per_second": round(rounds * 4 / baseline_total, 2),
            "peak_python_kib": round(peak / 1024, 1),
        }
        transport = Transport(httpx.AsyncClient(trust_env=False))
        provider = Provider(kind="http", endpoint=endpoint, concurrency=4, retries=0)
        agent = Agent(model="fixture", max_tokens=128)
        # Warm transport imports, then exclude warmup from measured connection count.
        await transport.complete(provider, agent, messages)
        connections.clear()
        modern = []
        tracemalloc.start()
        start = time.perf_counter()
        for _ in range(rounds):
            one = time.perf_counter()
            await asyncio.gather(
                *[transport.complete(provider, agent, messages) for _ in range(4)]
            )
            modern.append(time.perf_counter() - one)
        modern_total = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        result["scenarios"]["pooled_parallel"] = {
            **stats(modern),
            "connections": len(connections),
            "requests_per_second": round(rounds * 4 / modern_total, 2),
            "peak_python_kib": round(peak / 1024, 1),
        }
        await transport.close()
        result["independent_batch_speedup"] = round(
            statistics.median(baseline) / statistics.median(modern), 2
        )
        history = [{"role": "system", "content": "policy"}]
        for i in range(100):
            history += [
                {"role": "user", "content": f"Turn {i} " + ("x" * 300)},
                {"role": "assistant", "content": "y" * 300},
            ]
        bounded = bounded_messages(history, 6144)
        result["context"] = {
            "turns_archived": 100,
            "unbounded_request_bytes": len(json.dumps(history).encode()),
            "bounded_request_bytes": len(json.dumps(bounded).encode()),
            "messages_sent": len(bounded),
        }
        import pandas as pd

        with TemporaryDirectory() as temp:
            root = Path(temp)
            start = time.perf_counter()
            rows = []
            for i in range(60):
                rows.append({"role": "assistant", "content": "x" * 500})
                pd.DataFrame(rows).to_excel(root / "legacy.xlsx", index=False)
            excel = time.perf_counter() - start
            store = Store(root / "db")
            start = time.perf_counter()
            for i in range(60):
                store.message(
                    "benchmark", "agent", {"role": "assistant", "content": "x" * 500}
                )
            sqlite = time.perf_counter() - start
            store.close()
            result["persistence"] = {
                "messages": 60,
                "repeated_excel_ms": round(excel * 1000, 2),
                "incremental_sqlite_ms": round(sqlite * 1000, 2),
                "speedup": round(excel / sqlite, 2),
            }
        result["rss_mib_after"] = round(psutil.Process().memory_info().rss / 1024**2, 2)
        result["limitations"] = [
            "Synthetic loopback HTTP fixture, not real model inference.",
            "Parallelism applies only to independent agents; sequential dependencies are unchanged.",
            "Python allocation peaks exclude model-server memory and are not steady-state RSS comparisons.",
            "Context budget uses conservative UTF-8 bytes; it is not a provider tokenizer.",
            "Repeated Excel baseline reflects the legacy loop; on-demand export cost is deferred, not eliminated.",
        ]
        return result
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument(
        "--output", type=Path, default=Path("agenticai/docs/benchmark-results.json")
    )
    args = parser.parse_args()
    result = asyncio.run(benchmark(args.rounds))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
