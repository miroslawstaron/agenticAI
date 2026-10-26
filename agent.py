"""Backward-compatible synchronous agent, with pooled HTTP and safe exports."""

import csv
import html
import os
import re
import threading
import time
from pathlib import Path

import httpx

from agenticai.transport import bounded_messages


class AgentAI:
    def __init__(
        self, server_address, model_name, my_role, max_tokens=16000, api_key=""
    ):
        self.server_address = self.url = server_address
        self.model_name, self.max_tokens = model_name, max_tokens
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.messages = [{"role": "system", "content": my_role}]
        self.temperature, self.timeout, self.retries = 0.5, 300, 3
        self.context_tokens = 131072
        self.last_error = ""
        self._lock = threading.RLock()
        self._client = httpx.Client(
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=2)
        )

    def get_response(self, prompt):
        with self._lock:
            if not isinstance(prompt, str):
                self.last_error = "Prompt must be a string"
                return None
            pending = self.messages + [{"role": "user", "content": prompt}]
            try:
                messages = bounded_messages(
                    pending, self.context_tokens - self.max_tokens
                )
                headers = (
                    {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                )
                for attempt in range(self.retries):
                    try:
                        response = self._client.post(
                            self.url,
                            headers=headers,
                            json={
                                "model": self.model_name,
                                "messages": messages,
                                "stream": False,
                                "temperature": self.temperature,
                                "max_tokens": self.max_tokens,
                            },
                            timeout=self.timeout,
                        )
                        if response.status_code == 429 or response.status_code >= 500:
                            if attempt < self.retries - 1:
                                time.sleep(0.25 * 2**attempt)
                                continue
                        response.raise_for_status()
                        text = response.json()["choices"][0]["message"]["content"]
                        if not isinstance(text, str):
                            raise ValueError("Missing assistant text")
                        self.messages.extend(
                            [
                                {"role": "user", "content": prompt},
                                {"role": "assistant", "content": text},
                            ]
                        )
                        self.last_error = ""
                        return text
                    except (httpx.TimeoutException, httpx.TransportError):
                        if attempt == self.retries - 1:
                            raise
                        time.sleep(0.25 * 2**attempt)
            except (
                httpx.HTTPError,
                ValueError,
                KeyError,
                IndexError,
                TypeError,
            ) as exc:
                self.last_error = f"Model request failed: {type(exc).__name__}"
                return None

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def start(self):
        print(f"Starting agent with model {self.model_name} at {self.server_address}")

    def save_to_csv(self, filename):
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["role", "content"], delimiter="$")
            writer.writeheader()
            writer.writerows(self.messages)

    def save_to_excel(self, filename):
        import pandas as pd

        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(self.messages)
        for col in df.select_dtypes(include=["str", "object"]).columns:
            df[col] = df[col].map(
                lambda value: (
                    "'" + value
                    if isinstance(value, str) and value.startswith(("=", "+", "-", "@"))
                    else value
                )
            )
        df.to_excel(filename, index=False)

    def basic_markdown_to_html(self, text):
        text = html.escape(str(text))
        text = re.sub(
            r"```([a-z]*)\n(.*?)```",
            r'<pre><code class="\1">\2</code></pre>',
            text,
            flags=re.DOTALL,
        )
        text = re.sub(r"`([^`]*)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        return text.replace("\n", "<br>")

    def to_html(self, output_html, role1="Designer", role2="Programmer"):
        body = "".join(
            f"<tr><td>{html.escape(role1 if m['role'] == 'user' else role2)}</td><td>{self.basic_markdown_to_html(m['content'])}</td></tr>"
            for m in self.messages[1:]
        )
        Path(output_html).parent.mkdir(parents=True, exist_ok=True)
        Path(output_html).write_text(
            '<!doctype html><meta charset="utf-8"><title>Agent conversation</title><style>body{font:15px system-ui;margin:30px}td{padding:16px;border-bottom:1px solid #ddd;vertical-align:top}pre{white-space:pre-wrap}</style><table>'
            + body
            + "</table>",
            encoding="utf-8",
        )
