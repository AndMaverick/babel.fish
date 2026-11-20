"""Error types. Anything the command line should report with exit code 2 derives from BabelError."""
from __future__ import annotations


class BabelError(ValueError):
    """The input, a profile, a glossary or a backend setting could not be used."""


class BackendError(BabelError):
    """A translation backend failed (network, status code, malformed reply)."""
