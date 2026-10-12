"""Problem error DTO and exception used for all API error responses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Problem:
    """Wire shape of an API error response."""

    code: str
    message: str
    requestId: str  # noqa: N815 - wire-format field name
    docsUrl: str  # noqa: N815 - wire-format field name


class ProblemError(Exception):
    """Raised by handlers/guards to produce a Problem response with an HTTP status."""

    def __init__(self, status: int, code: str, message: str) -> None:
        """Store the HTTP status, stable error code and human message."""
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
