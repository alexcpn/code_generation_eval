"""
CHALLENGE: Off-by-One Pagination
CATEGORY: algorithmic_correctness
DIFFICULTY: 1
POINTS: 8
WHY: Models routinely get boundary math wrong in pagination — returning empty last pages,
     skipping items, or crashing on edge inputs. This is the #1 subtle bug in AI-generated code.
"""

PROMPT = """
Write a function `paginate(items: list, page: int, page_size: int) -> dict` that returns:

{
    "items": [...],        # items for the requested page (1-indexed)
    "page": int,           # current page number
    "page_size": int,      # requested page size
    "total_items": int,    # total number of items
    "total_pages": int,    # total number of pages
    "has_next": bool,      # whether there is a next page
    "has_prev": bool       # whether there is a previous page
}

Requirements:
- Pages are 1-indexed (first page is page=1)
- If page is out of range, return empty items but correct metadata
- If items is empty, return total_pages=0, page=1
- page_size must be > 0, raise ValueError otherwise
- page must be >= 1, raise ValueError otherwise
"""

# --- Tests (model never sees below this line) ---

import pytest
import importlib


def load():
    mod = importlib.import_module("solutions.c01_off_by_one")
    return mod.paginate


class TestPagination:
    """8 points total: 1 per test."""

    def test_basic_first_page(self):
        """(1 pt) First page of simple data."""
        paginate = load()
        result = paginate([1, 2, 3, 4, 5], page=1, page_size=2)
        assert result["items"] == [1, 2]
        assert result["has_next"] is True
        assert result["has_prev"] is False

    def test_basic_last_page(self):
        """(1 pt) Last page with fewer items than page_size."""
        paginate = load()
        result = paginate([1, 2, 3, 4, 5], page=3, page_size=2)
        assert result["items"] == [5]
        assert result["total_pages"] == 3
        assert result["has_next"] is False
        assert result["has_prev"] is True

    def test_exact_fit(self):
        """(1 pt) Items divide evenly into pages — no off-by-one on total_pages."""
        paginate = load()
        result = paginate([1, 2, 3, 4], page=2, page_size=2)
        assert result["total_pages"] == 2  # NOT 3
        assert result["items"] == [3, 4]
        assert result["has_next"] is False

    def test_single_item(self):
        """(1 pt) Single item, single page."""
        paginate = load()
        result = paginate(["only"], page=1, page_size=10)
        assert result["items"] == ["only"]
        assert result["total_pages"] == 1
        assert result["has_next"] is False
        assert result["has_prev"] is False

    def test_empty_list(self):
        """(1 pt) Empty list — should not crash, total_pages=0."""
        paginate = load()
        result = paginate([], page=1, page_size=5)
        assert result["items"] == []
        assert result["total_pages"] == 0
        assert result["total_items"] == 0

    def test_page_beyond_range(self):
        """(1 pt) Page number exceeds total — empty items, correct metadata."""
        paginate = load()
        result = paginate([1, 2, 3], page=99, page_size=2)
        assert result["items"] == []
        assert result["total_pages"] == 2
        assert result["total_items"] == 3

    def test_invalid_page_size(self):
        """(1 pt) page_size=0 or negative raises ValueError."""
        paginate = load()
        with pytest.raises(ValueError):
            paginate([1, 2], page=1, page_size=0)
        with pytest.raises(ValueError):
            paginate([1, 2], page=1, page_size=-1)

    def test_invalid_page_number(self):
        """(1 pt) page=0 or negative raises ValueError."""
        paginate = load()
        with pytest.raises(ValueError):
            paginate([1, 2], page=0, page_size=2)
        with pytest.raises(ValueError):
            paginate([1, 2], page=-1, page_size=2)
