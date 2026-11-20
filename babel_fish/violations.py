"""What the verifier reports."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Violation:
    code: str
    severity: str          # "error" blocks a result, "warning" is reported
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "severity": self.severity, "message": self.message}


def errors(vs: list[Violation]) -> list[Violation]:
    return [v for v in vs if v.severity == "error"]
