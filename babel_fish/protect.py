"""Protected spans: placeholders, markup, links, e-mail addresses and code are swapped for numbered tokens before translation and put back after,
so no backend can reword them. A reply that loses, repeats or invents a token is caught by the verifier."""
from __future__ import annotations

import re
from dataclasses import dataclass

OPEN, CLOSE = "⟦", "⟧"
_PATTERN = re.compile("|".join([
    r"\{\{[^{}\n]+\}\}", r"\$\{[^{}\n]+\}", r"\{[A-Za-z_][\w.]*\}", r"%\([A-Za-z_]\w*\)[sdif]", r"%[sdif](?![A-Za-z])",
    r"</?[A-Za-z][^<>\n]*>", r"https?://[^\s<>\"')\]]+", r"[\w.+-]+@[\w-]+\.[\w.-]+", r"`[^`\n]+`",
]))
TOKEN = re.compile(f"{OPEN}(\\d+){CLOSE}")


@dataclass(frozen=True)
class Masked:
    text: str
    spans: tuple[str, ...]

    @property
    def tokens(self) -> tuple[str, ...]:
        return tuple(f"{OPEN}{i}{CLOSE}" for i in range(1, len(self.spans) + 1))


def mask(text: str) -> Masked:
    spans: list[str] = []

    def sub(m: re.Match[str]) -> str:
        spans.append(m.group(0))
        return f"{OPEN}{len(spans)}{CLOSE}"

    return Masked(_PATTERN.sub(sub, text), tuple(spans))


def unmask(text: str, spans: tuple[str, ...]) -> str:
    return TOKEN.sub(lambda m: spans[int(m.group(1)) - 1] if 1 <= int(m.group(1)) <= len(spans) else m.group(0), text)


def token_problems(output: str, count: int) -> tuple[list[str], list[str], list[str]]:
    """(missing, repeated, unknown) tokens in ``output``, given that the source had tokens 1..count once each."""
    found = [int(n) for n in TOKEN.findall(output)]
    missing = [f"{OPEN}{i}{CLOSE}" for i in range(1, count + 1) if found.count(i) == 0]
    repeated = [f"{OPEN}{i}{CLOSE}" for i in range(1, count + 1) if found.count(i) > 1]
    unknown = sorted({f"{OPEN}{n}{CLOSE}" for n in found if not 1 <= n <= count})
    return missing, repeated, unknown
