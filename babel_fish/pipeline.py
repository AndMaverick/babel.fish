"""translate(): mask protected text, ask the backend, verify the reply, and on an error ask again with the problems spelled out.

Every attempt is kept. The result is the attempt with the fewest errors (the later one on a tie), so a repair that makes things worse is never returned."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import langid, prompt, protect, verify
from .backends import Backend
from .errors import BabelError
from .glossary import Glossary
from .profiles import Profile
from .violations import Violation, errors


@dataclass(frozen=True)
class Attempt:
    request_sha256: str
    reply: str
    violations: tuple[Violation, ...]
    cached: bool = False


@dataclass(frozen=True)
class Result:
    text: str
    ok: bool
    source_language: str
    profile: Profile
    attempts: tuple[Attempt, ...]
    chosen: int
    violations: tuple[Violation, ...] = field(default=())

    def to_dict(self) -> dict[str, object]:
        return {"text": self.text, "ok": self.ok, "source_language": self.source_language,
                "profile": {"language": self.profile.language, "tone": self.profile.tone, "context": self.profile.context},
                "chosen_attempt": self.chosen + 1,
                "attempts": [{"request_sha256": a.request_sha256, "cached": a.cached, "violations": [v.to_dict() for v in a.violations]} for a in self.attempts]}


class Cache:
    """Append-only JSON lines keyed by the SHA-256 of the whole request, so a repeated run costs nothing and gives the same reply."""

    def __init__(self, path: str | None) -> None:
        self.path = Path(path) if path else None
        self.data: dict[str, str] = {}
        if self.path and self.path.exists():
            for n, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    self.data[row["key"]] = row["reply"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    raise BabelError(f"{self.path}: line {n} is not a cache entry") from None

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def put(self, key: str, reply: str) -> None:
        self.data[key] = reply
        if self.path:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, "reply": reply}, ensure_ascii=False, sort_keys=True) + "\n")


def request_key(backend_id: str, system: str, user: str) -> str:
    body = json.dumps({"backend": backend_id, "system": system, "user": user}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def translate(text: str, profile: Profile, backend: Backend, *, glossary: Glossary | None = None, source_language: str | None = None,
              max_attempts: int = 3, cache: Cache | None = None, protect_spans: bool = True) -> Result:
    if not text.strip():
        raise BabelError("nothing to translate")
    if max_attempts < 1:
        raise BabelError("max_attempts must be at least 1")
    cache = cache or Cache(None)
    src_lang = source_language or langid.identify(text)
    if src_lang == "unknown":
        src_lang = "en"
    masked = protect.mask(text) if protect_spans else protect.Masked(text, ())
    system = prompt.system_prompt(profile, glossary, len(masked.spans))
    user = masked.text
    attempts: list[Attempt] = []
    previous = ""
    for _n in range(max_attempts):
        key = request_key(backend.id, system, user)
        reply = cache.get(key)
        cached = reply is not None
        if reply is None:
            reply = backend.complete(system, user).strip()
            cache.put(key, reply)
        problems = verify.check(masked.text, reply, source_lang=src_lang, target_lang=profile.language, tone=profile.tone,
                                context=profile.context, spans=len(masked.spans), glossary=glossary)
        attempts.append(Attempt(key, reply, tuple(problems), cached))
        if not errors(problems):
            break
        previous = reply
        user = prompt.repair_prompt(masked.text, previous, errors(problems))
    chosen = min(range(len(attempts)), key=lambda i: (len(errors(list(attempts[i].violations))), -i))
    best = attempts[chosen]
    final = protect.unmask(best.reply, masked.spans)
    return Result(final, not errors(list(best.violations)), src_lang, profile, tuple(attempts), chosen, best.violations)
