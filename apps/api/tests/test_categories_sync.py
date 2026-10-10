from pathlib import Path

from categories import CATEGORIES, category_for_type


def test_bundled_copy_matches_ssot():
    """The image-bundled copy must byte-match the canonical SSOT."""
    repo_root = Path(__file__).resolve().parents[3]
    canonical = (repo_root / "apis/v1/categories.yaml").read_text()
    bundled = (repo_root / "apps/api/categories.yaml").read_text()
    assert (
        bundled == canonical
    ), "apps/api/categories.yaml drifted from apis/v1/categories.yaml"


def test_category_for_type():
    assert category_for_type("postgres") == "database"
    assert category_for_type("clickhouse") == "analytics"
    assert category_for_type("made-up") is None


def test_categories_constant():
    assert CATEGORIES == frozenset(
        {"database", "object", "volume", "streaming", "search", "analytics"}
    )
