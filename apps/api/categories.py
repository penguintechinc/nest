"""Type→category mapping for the API, loaded from the image-bundled SSOT copy.

The canonical source is apis/v1/categories.yaml; apps/api/categories.yaml is a
drift-tested byte copy shipped in the container (the Go tree is not present at
runtime). See tests/test_categories_sync.py.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_MAP_PATH = Path(__file__).with_name("categories.yaml")

_category_to_types: dict[str, list[str]] = yaml.safe_load(_MAP_PATH.read_text())
_TYPE_TO_CATEGORY: dict[str, str] = {
    t: cat for cat, types in _category_to_types.items() for t in types
}

CATEGORIES: frozenset[str] = frozenset(_category_to_types.keys())


def category_for_type(engine_type: str) -> str | None:
    """Return the category owning ``engine_type``, or None if unknown."""
    return _TYPE_TO_CATEGORY.get(engine_type)
