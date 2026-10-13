"""Model gateway: a chain of providers with a fallback rung, plus a fake for offline tests.

Chain order (each rung is tried in turn; any error, timeout or unusable answer falls to the next):
  1. Tencent Hunyuan, via its OpenAI-compatible endpoint   (HUNYUAN_API_KEY)
  2. Any other OpenAI-compatible endpoint                  (LLM_FALLBACK_BASE_URL / _API_KEY / _MODEL)
  3. No model: rules for understand(), templates for write(). Always available.

Standard library only, so the language layer adds no dependencies to the backend.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Protocol

HUNYUAN_BASE_URL = "https://api.hunyuan.cloud.tencent.com/v1"
HUNYUAN_MODEL = "hunyuan-turbos-latest"


class ModelError(Exception):
    pass


class Gateway(Protocol):
    name: str

    def complete(self, system: str, user: str, *, want_json: bool = False) -> str: ...


@dataclass
class OpenAICompatible:
    """Any /chat/completions endpoint: Hunyuan, or a fallback provider."""
    name: str
    base_url: str
    api_key: str
    model: str
    timeout: float = 12.0

    def complete(self, system: str, user: str, *, want_json: bool = False) -> str:
        body: dict = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
        }
        if want_json:
            body["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.load(resp)
            return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as e:
            raise ModelError(f"{self.name}: {e}") from e


@dataclass
class FakeGateway:
    """Offline stand-in for tests and demos without a key.

    `script` maps a predicate on the user prompt to a reply; the first match wins.
    With no match it raises, so the caller exercises its no-model fallback.
    """
    name: str = "fake"
    script: list[tuple[Callable[[str], bool], str]] = field(default_factory=list)
    calls: list[tuple[str, str]] = field(default_factory=list)

    def reply(self, when: Callable[[str], bool] | str, text: str) -> "FakeGateway":
        pred = when if callable(when) else (lambda u, s=when: s in u)
        self.script.append((pred, text))
        return self

    def complete(self, system: str, user: str, *, want_json: bool = False) -> str:
        self.calls.append((system, user))
        for pred, text in self.script:
            if pred(user):
                return text
        raise ModelError("fake: no scripted reply")


@dataclass
class Chain:
    rungs: list[Gateway]

    @property
    def name(self) -> str:
        return " > ".join(g.name for g in self.rungs) or "none"

    def complete(self, system: str, user: str, *, want_json: bool = False,
                 accept: Callable[[str], bool] = lambda _: True) -> tuple[str, str]:
        """(reply, which rung answered). Raises ModelError if every rung fails or is rejected by `accept`."""
        errors = []
        for g in self.rungs:
            try:
                out = g.complete(system, user, want_json=want_json)
            except ModelError as e:
                errors.append(str(e))
                continue
            if accept(out):
                return out, g.name
            errors.append(f"{g.name}: unusable reply")
        raise ModelError("; ".join(errors) or "no model configured")


def from_env(env: dict | None = None) -> Chain:
    env = os.environ if env is None else env
    rungs: list[Gateway] = []
    if env.get("HUNYUAN_API_KEY"):
        rungs.append(OpenAICompatible(
            name="hunyuan",
            base_url=env.get("HUNYUAN_BASE_URL", HUNYUAN_BASE_URL),
            api_key=env["HUNYUAN_API_KEY"],
            model=env.get("HUNYUAN_MODEL", HUNYUAN_MODEL),
        ))
    if env.get("LLM_FALLBACK_BASE_URL") and env.get("LLM_FALLBACK_API_KEY") and env.get("LLM_FALLBACK_MODEL"):
        rungs.append(OpenAICompatible(
            name=env.get("LLM_FALLBACK_NAME", "fallback"),
            base_url=env["LLM_FALLBACK_BASE_URL"],
            api_key=env["LLM_FALLBACK_API_KEY"],
            model=env["LLM_FALLBACK_MODEL"],
        ))
    return Chain(rungs)


_default: Chain | None = None


def default_chain() -> Chain:
    global _default
    if _default is None:
        _default = from_env()
    return _default


def describe() -> dict:
    """For GET /meta: the model chain, in order, ending in the no-model rung."""
    return {"model_chain": [g.name for g in default_chain().rungs] + ["rules+templates"]}


def as_chain(g: Gateway | Chain | None) -> Chain:
    if g is None:
        return default_chain()
    return g if isinstance(g, Chain) else Chain([g])
