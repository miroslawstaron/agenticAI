"""Versioned configuration shared by the API, CLI and runtime."""

from __future__ import annotations

import re
from typing import Any, Literal
from uuid import uuid4

from jsonschema import Draft202012Validator, SchemaError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def identifier() -> str:
    return uuid4().hex[:12]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("id", check_fields=False)
    @classmethod
    def safe_id(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value):
            raise ValueError(
                "IDs must be 1–64 letters, numbers, dots, underscores or hyphens, starting with a letter or number"
            )
        return value


class Provider(Model):
    id: str = Field(default_factory=identifier)
    name: str = "Demo provider"
    kind: Literal["demo", "http"] = "demo"
    endpoint: str = "http://localhost:11434/v1/chat/completions"
    api_key_env: str = ""
    supports_tools: bool = False
    timeout: float = Field(300, gt=0, le=3600)
    retries: int = Field(2, ge=0, le=5)
    concurrency: int = Field(2, ge=1, le=64)

    @field_validator("endpoint")
    @classmethod
    def http_endpoint(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("Endpoint must be an HTTP(S) URL")
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if (
            not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "Use an endpoint without credentials, query parameters or fragments"
            )
        return value.rstrip("/")


class Tool(Model):
    id: str = Field(default_factory=identifier)
    name: str = "New tool"
    description: str = ""
    kind: Literal["cli", "shell", "compiler", "analyzer", "python"] = "cli"
    executable: str = ""
    args: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}}
    )
    stdin: str = ""
    cwd: str = ""
    env: dict[str, str] = Field(
        default_factory=dict, description="Variable name to host variable reference"
    )
    timeout: float = Field(60, gt=0, le=3600)
    accepted_exit_codes: list[int] = Field(default_factory=lambda: [0])
    output_format: Literal["text", "json", "artifact"] = "text"
    artifacts: list[str] = Field(default_factory=list)
    max_output: int = Field(12000, ge=256, le=200000)
    version_args: list[str] = Field(default_factory=lambda: ["--version"])
    plugin: str = ""

    @field_validator("input_schema")
    @classmethod
    def valid_schema(cls, value: dict) -> dict:
        try:
            Draft202012Validator.check_schema(value)
        except SchemaError as exc:
            raise ValueError("Invalid JSON Schema: " + exc.message) from exc
        if value.get("type") != "object":
            raise ValueError("Tool input schema must describe an object")
        return value


class Agent(Model):
    id: str = Field(default_factory=identifier)
    name: str = "New agent"
    role: str = "You are a helpful collaborator."
    provider_id: str = "demo"
    model: str = "demo"
    temperature: float = Field(0.5, ge=0, le=2)
    max_tokens: int = Field(2048, ge=1, le=1000000)
    context_tokens: int = Field(8192, ge=256, le=2000000)
    tools: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    can_orchestrate: bool = False
    x: float = 0
    y: float = 0
    kind: Literal["agent", "human", "tool", "join"] = "agent"
    tool_id: str = ""
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    max_visits: int = Field(5, ge=1, le=1000)


class Link(Model):
    id: str = Field(default_factory=identifier)
    source: str
    target: str
    template: str = "{message}"
    condition: Literal["always", "contains", "not_contains", "equals"] = "always"
    value: str = ""

    def matches(self, text: str) -> bool:
        return {
            "always": lambda: True,
            "contains": lambda: self.value in text,
            "not_contains": lambda: self.value not in text,
            "equals": lambda: self.value == text,
        }[self.condition]()


class Limits(Model):
    concurrency: int = Field(4, ge=1, le=64)
    tool_concurrency: int = Field(4, ge=1, le=64)
    max_agents: int = Field(16, ge=1, le=256)
    max_calls: int = Field(100, ge=1, le=10000)
    max_steps: int = Field(200, ge=1, le=10000)
    active_seconds: float = Field(1200, gt=0, le=86400)


class Network(Model):
    schema_version: Literal[1] = 1
    id: str = Field(default_factory=identifier)
    name: str = "Untitled network"
    description: str = ""
    mode: Literal["workflow", "autonomous"] = "workflow"
    initial_task: str = Field(default="", max_length=1000000)
    agents: list[Agent] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    entry_agents: list[str] = Field(default_factory=list)
    limits: Limits = Field(default_factory=Limits)

    @model_validator(mode="after")
    def check_graph(self):
        ids = [a.id for a in self.agents]
        if len(set(ids)) != len(ids):
            raise ValueError("Agent ids must be unique")
        if len(self.agents) > self.limits.max_agents:
            raise ValueError("Network exceeds agent limit")
        if any(link.source not in ids or link.target not in ids for link in self.links):
            raise ValueError("Every link must reference existing agents")
        if any(a not in ids for a in self.entry_agents):
            raise ValueError("Entry agent does not exist")
        return self


class RunRequest(Model):
    network: Network
    prompt: str | None = Field(default=None, min_length=1, max_length=1000000)


class InstallRequest(Model):
    manager: Literal["pip", "npm", "winget", "apt", "recipe"]
    package: str = Field(min_length=1, max_length=200)
    version: str = ""
    source: str = ""
    action: Literal["install", "update", "remove"] = "install"
    recipe_id: str = ""

    @field_validator("package", "version", "source")
    @classmethod
    def safe_package(cls, value: str) -> str:
        if value and (
            not re.fullmatch(r"[A-Za-z0-9@_./:+~=<>-]+", value) or value.startswith("-")
        ):
            raise ValueError(
                "Use a package identifier/version/source, not command-line flags"
            )
        return value


class Recipe(Model):
    id: str = Field(default_factory=identifier)
    name: str
    executable: str
    install_args: list[str]
    update_args: list[str] = Field(default_factory=list)
    remove_args: list[str] = Field(default_factory=list)
    timeout: float = Field(600, gt=0, le=3600)


class ExecutionResult(Model):
    ok: bool = False
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration: float = 0
    timed_out: bool = False
    artifacts: list[str] = Field(default_factory=list)
    data: Any = None
    error: str = ""
