"""CrdRepository interface seam: types, errors and the Protocol consumers depend on.

Task 4 (app factory) and Task 11 consume ``CrdRepository`` / ``Unavailable`` before the
concrete ``KubeCrdRepository`` lands in Task 12. This module is that seam; Task 12 adds the
implementation here without changing any name defined below.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True, frozen=True)
class DataResourceView:
    """Read model of a ``DataResource`` custom resource scoped to one tenant."""

    name: str
    namespace: str
    type: str
    klass: str
    tenant: str
    phase: str
    ha: bool
    endpoints: dict[str, str] | None
    health: dict[str, str] | None


@dataclass(slots=True, frozen=True)
class CreateSpec:
    """Caller-supplied fields for creating a managed ``DataResource``."""

    name: str
    type: str
    klass: str
    size: str | None
    ha: bool


@dataclass(slots=True, frozen=True)
class PatchSpec:
    """Mutable fields of a ``DataResource``; ``None`` means leave unchanged."""

    size: str | None
    ha: bool | None
    klass: str | None


class RepoError(Exception):
    """Base class for every CrdRepository failure."""


class NotFound(RepoError):
    """The named resource does not exist for this tenant."""


class AlreadyExists(RepoError):
    """A resource with that name already exists for this tenant."""


class TenantMismatch(RepoError):
    """The stored resource belongs to a different tenant than the caller."""


class Unavailable(RepoError):
    """The backing cluster could not be reached or timed out; callers map to 503."""


class CrdRepository(Protocol):
    """Async, tenant-scoped access to ``DataResource`` custom resources."""

    async def list(self, tenant: str) -> list[DataResourceView]:
        """Return every DataResource owned by ``tenant``."""
        ...

    async def get(self, tenant: str, name: str) -> DataResourceView:
        """Return one DataResource or raise NotFound / TenantMismatch."""
        ...

    async def create(self, tenant: str, spec: CreateSpec) -> DataResourceView:
        """Create a managed DataResource or raise AlreadyExists."""
        ...

    async def patch(self, tenant: str, name: str, patch: PatchSpec) -> DataResourceView:
        """Apply ``patch`` to a DataResource and return the updated view."""
        ...

    async def delete(self, tenant: str, name: str) -> None:
        """Delete a DataResource or raise NotFound / TenantMismatch."""
        ...
