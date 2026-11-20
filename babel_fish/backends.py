"""Backends: anything that turns (system prompt, user text) into a reply. HTTP uses the standard library, never prints a key and retries only
what is worth retrying (429 and 5xx), waiting as the server asks (capped)."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Protocol

from .errors import BabelError, BackendError


class Backend(Protocol):
    id: str

    def complete(self, system: str, user: str) -> str: ...


class FixtureBackend:
    """Deterministic, offline: replies come from a table keyed by the user text, or from a function."""

    id = "fixture"

    def __init__(self, replies: dict[str, str] | Callable[[str, str], str]) -> None:
        self.replies = replies
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if callable(self.replies):
            return self.replies(system, user)
        if user not in self.replies:
            raise BackendError(f"fixture has no reply for: {user[:60]!r}")
        return self.replies[user]


def _post(url: str, headers: dict[str, str], body: dict[str, object], timeout: float, retries: int, sleep: Callable[[float], None]) -> dict[str, object]:
    data = json.dumps(body).encode("utf-8")
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:             # noqa: S310  (the URL is set by the user)
                parsed = json.loads(resp.read().decode("utf-8"))
                if not isinstance(parsed, dict):
                    raise BackendError("the service replied with something other than a JSON object")
                return parsed
        except urllib.error.HTTPError as e:
            retriable = e.code == 429 or 500 <= e.code < 600
            if retriable and attempt < retries:
                wait = e.headers.get("Retry-After") if e.headers else None
                sleep(min(float(wait), 20.0) if wait and wait.replace(".", "", 1).isdigit() else min(2.0 ** attempt, 20.0))
                continue
            raise BackendError(f"the service answered HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < retries:
                sleep(min(2.0 ** attempt, 20.0))
                continue
            raise BackendError(f"cannot reach {url.split('?')[0]}: {getattr(e, 'reason', e)}") from None
        except json.JSONDecodeError:
            raise BackendError("the service replied with text that is not JSON") from None
    raise BackendError("unreachable")


class OpenAICompatible:
    """Chat completions at ``{base_url}/chat/completions``: OpenAI, and any server that speaks the same protocol (vLLM, llama.cpp, Ollama)."""

    def __init__(self, model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1", api_key: str | None = None,
                 timeout: float = 60.0, retries: int = 3, sleep: Callable[[float], None] = time.sleep) -> None:
        self.model, self.base_url, self.timeout, self.retries, self.sleep = model, base_url.rstrip("/"), timeout, retries, sleep
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self.id = f"openai:{base_url.rstrip('/')}:{model}"

    def complete(self, system: str, user: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        body = {"model": self.model, "temperature": 0, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        reply = _post(f"{self.base_url}/chat/completions", headers, body, self.timeout, self.retries, self.sleep)
        try:
            return str(reply["choices"][0]["message"]["content"]).strip()          # type: ignore[index]
        except (KeyError, IndexError, TypeError):
            raise BackendError("the reply has no choices[0].message.content") from None


class AnthropicMessages:
    """The Anthropic Messages API."""

    def __init__(self, model: str, base_url: str = "https://api.anthropic.com", api_key: str | None = None, max_tokens: int = 4096,
                 timeout: float = 60.0, retries: int = 3, sleep: Callable[[float], None] = time.sleep) -> None:
        self.model, self.base_url, self.max_tokens, self.timeout, self.retries, self.sleep = model, base_url.rstrip("/"), max_tokens, timeout, retries, sleep
        self.api_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
        self.id = f"anthropic:{base_url.rstrip('/')}:{model}"

    def complete(self, system: str, user: str) -> str:
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        body = {"model": self.model, "max_tokens": self.max_tokens, "temperature": 0, "system": system, "messages": [{"role": "user", "content": user}]}
        reply = _post(f"{self.base_url}/v1/messages", headers, body, self.timeout, self.retries, self.sleep)
        try:
            return "".join(str(b["text"]) for b in reply["content"] if b.get("type") == "text").strip()   # type: ignore[attr-defined]
        except (KeyError, TypeError, AttributeError):
            raise BackendError("the reply has no text content") from None


def from_environment(name: str | None, model: str | None, base_url: str | None) -> Backend:
    """Pick a backend by name, or by whichever API key is set."""
    if name is None:
        name = "openai" if os.environ.get("OPENAI_API_KEY") else "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else None
    if name == "openai":
        if not os.environ.get("OPENAI_API_KEY") and not base_url:
            raise BabelError("set OPENAI_API_KEY, or pass --base-url for a local server")
        return OpenAICompatible(model or "gpt-4o-mini", base_url or "https://api.openai.com/v1")
    if name == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise BabelError("set ANTHROPIC_API_KEY")
        if not model:
            raise BabelError("--model is required for the anthropic backend")
        return AnthropicMessages(model, base_url or "https://api.anthropic.com")
    raise BabelError("no backend: set OPENAI_API_KEY or ANTHROPIC_API_KEY, or choose --backend openai|anthropic")
