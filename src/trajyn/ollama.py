"""Opt-in adapter for an already-running local Ollama server."""

import json
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPException
from typing import Literal
from urllib.parse import urlsplit

from trajyn.agent import AgentContext
from trajyn.models import AgentDecision, AgentIdentity, Scalar, ToolAction, ToolSpec, Usage
from trajyn.recording import encode_json

PROMPT_REVISION = 2


@dataclass(frozen=True, slots=True)
class LocalModel:
    name: str
    digest: str
    family: str
    supports_thinking: bool


@dataclass(frozen=True, slots=True)
class InferenceOptions:
    seed: int = 17
    context_tokens: int = 4096
    output_tokens: int = 160
    timeout_seconds: int = 30
    tool_mode: Literal["native", "json"] = "native"


class OllamaError(ValueError):
    pass


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise OllamaError("expected a JSON object")
    return value


class OllamaConnection:
    def __init__(self, url: str, options: InferenceOptions = InferenceOptions()) -> None:
        address = urlsplit(url)
        host = address.hostname
        if (
            address.scheme != "http"
            or host not in {"127.0.0.1", "::1", "localhost"}
            or address.username is not None
            or address.password is not None
            or address.path not in {"", "/"}
            or address.query
            or address.fragment
        ):
            raise ValueError("Ollama URL must address a local loopback HTTP server")
        assert host is not None
        self.host = host
        self.port = address.port or 11434
        self.options = options

    def api(self, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
        connection = HTTPConnection(self.host, self.port, timeout=self.options.timeout_seconds)
        try:
            if payload is None:
                connection.request("GET", path)
            else:
                connection.request(
                    "POST",
                    path,
                    encode_json(payload).encode("utf-8"),
                    {"Content-Type": "application/json"},
                )
            with connection.getresponse() as response:
                if response.status != 200:
                    raise OllamaError(f"Ollama request failed with HTTP {response.status}")
                return _object(json.loads(response.read()))
        except (HTTPException, OSError, json.JSONDecodeError) as error:
            raise OllamaError(f"Ollama response unavailable ({type(error).__name__})") from error
        finally:
            connection.close()

    def model(self, name: str) -> LocalModel:
        tags = self.api("/api/tags").get("models")
        if not isinstance(tags, list):
            raise OllamaError("Ollama model catalog unavailable")
        for tag in map(_object, tags):
            if tag.get("name") != name:
                continue
            digest, size = tag.get("digest"), tag.get("size")
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or type(size) is not int
                or size <= 0
            ):
                raise OllamaError(f"{name} is missing a local weight file or digest")
            detail = self.api("/api/show", {"model": name})
            family = _object(detail.get("details")).get("family")
            capabilities = detail.get("capabilities")
            if (
                not isinstance(family, str)
                or not isinstance(capabilities, list)
                or "tools" not in capabilities
            ):
                raise OllamaError(f"{name} does not advertise a model family and tool calling")
            return LocalModel(name, digest, family, "thinking" in capabilities)
        raise OllamaError(f"model {name} is absent from the local Ollama catalog")


def _arguments(tool: ToolSpec) -> dict[str, object]:
    return {
        "type": "object",
        "required": [parameter.name for parameter in tool.parameters],
        "properties": {
            parameter.name: {"type": "string", "description": parameter.description}
            for parameter in tool.parameters
        },
        "additionalProperties": False,
    }


def _tool(tool: ToolSpec) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": _arguments(tool),
        },
    }


def _messages(context: AgentContext, *, structured: bool = False) -> list[dict[str, object]]:
    system = (
        "You operate a synthetic delivery-support service. Make exactly one listed tool call "
        "per turn using identifiers from this task and its tool results. Use the authoritative "
        "carrier observation to decide the remedy. Build on successful results already in "
        "the history and choose the next unfinished operation. Repeat a call only when "
        "the result says it can be retried. Use the refund fallback after an out-of-stock "
        "response. Close the case once a remedy receipt is available."
    )
    task = context.task.goal
    if context.memory is not None:
        task += (
            "\nHistorical example or guidance follows. Reuse applicable procedure only. "
            "Use current identifiers. A binding with source_step 0 comes from the current "
            "task. Other bindings refer to earlier observations. Continue independently "
            "if a tool or expected observation differs.\n" + encode_json(context.memory)
        )
    if structured:
        system += " Return a JSON object with tool and arguments fields."
        task += "\nAvailable tools:\n" + encode_json(context.tools)
        task += "\nPublic tool history in order:\n" + encode_json(
            [{"action": step.action, "observation": step.observation} for step in context.steps]
        )
        task += "\nChoose the single next tool call that advances the case."
    messages: list[dict[str, object]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": task},
    ]
    if structured:
        return messages
    for step in context.steps:
        messages.extend(
            (
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "index": 0,
                                "name": step.action.tool,
                                "arguments": step.action.arguments,
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_name": step.action.tool,
                    "content": encode_json(step.observation),
                },
            )
        )
    return messages


def _response_schema(tools: tuple[ToolSpec, ...]) -> dict[str, object]:
    return {
        "anyOf": [
            {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "enum": [tool.name]},
                    "arguments": _arguments(tool),
                },
                "required": ["tool", "arguments"],
                "additionalProperties": False,
            }
            for tool in tools
        ]
    }


def _token_count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


class OllamaAgent:
    def __init__(self, connection: OllamaConnection, model: LocalModel) -> None:
        self.connection = connection
        self.model = model
        self.identity = AgentIdentity("ollama", model.name, model.digest)
        self.call_count = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.termination: str | None = None

    def decide(self, context: AgentContext) -> AgentDecision | None:
        if context.steps and context.steps[-1].observation.code == "case_closed":
            self.termination = "observed_case_closed"
            return None

        options = self.connection.options
        structured = options.tool_mode == "json"
        payload: dict[str, object] = {
            "model": self.model.name,
            "stream": False,
            "keep_alive": "3m",
            "messages": _messages(context, structured=structured),
            "options": {
                "seed": options.seed,
                "num_ctx": options.context_tokens,
                "num_predict": options.output_tokens,
                "temperature": 0,
            },
        }
        if self.model.supports_thinking:
            payload["think"] = False
        if structured:
            payload["format"] = _response_schema(context.tools)
        else:
            payload["tools"] = [_tool(tool) for tool in context.tools]
        self.call_count += 1
        try:
            response = self.connection.api("/api/chat", payload)
            inputs = _token_count(response.get("prompt_eval_count"))
            outputs = _token_count(response.get("eval_count"))
            self.input_tokens += inputs or 0
            self.output_tokens += outputs or 0

            message = _object(response.get("message"))
            if structured:
                content = message.get("content")
                if not isinstance(content, str) or not content:
                    raise OllamaError("model_returned_no_action_json")
                try:
                    function = _object(json.loads(content))
                except json.JSONDecodeError as error:
                    raise OllamaError("model_returned_invalid_action_json") from error
                name = function.get("tool")
            else:
                calls = message.get("tool_calls", [])
                if not isinstance(calls, list):
                    raise OllamaError("invalid tool_calls response")
                if not calls:
                    self.termination = "model_returned_no_tool"
                    return None
                function = _object(_object(calls[0]).get("function"))
                name = function.get("name")
            if not isinstance(name, str):
                raise OllamaError("tool call has no name")
            arguments: dict[str, Scalar] = {}
            for field, value in _object(function.get("arguments")).items():
                if value is None or isinstance(value, (str, bool, int, float)):
                    arguments[field] = value
                else:
                    raise OllamaError("tool argument is not a JSON scalar")
            return AgentDecision(ToolAction(name, arguments), Usage(inputs, outputs))
        except OllamaError as error:
            self.termination = str(error)
            return None
