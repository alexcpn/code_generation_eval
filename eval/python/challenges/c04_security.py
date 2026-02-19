"""
CHALLENGE: Secure Query Builder
CATEGORY: security
DIFFICULTY: 2
POINTS: 15
WHY: Models generate SQL with string formatting. Even when told "use parameterised queries",
     they often miss secondary injection points (ORDER BY, LIMIT, table names) or build
     filters with f-strings. This challenge has multiple injection surfaces.
"""

PROMPT = """
Write a class `SafeQueryBuilder` that builds SELECT queries safely.

```python
class SafeQueryBuilder:
    ALLOWED_TABLES = {"users", "orders", "products"}
    ALLOWED_COLUMNS = {
        "users": {"id", "name", "email", "created_at"},
        "orders": {"id", "user_id", "total", "status", "created_at"},
        "products": {"id", "name", "price", "category"},
    }
    ALLOWED_ORDER_DIRS = {"ASC", "DESC"}

    def __init__(self, table: str):
        \"\"\"Initialize with table name. Raise ValueError if table not in ALLOWED_TABLES.\"\"\"

    def select(self, columns: list[str]) -> "SafeQueryBuilder":
        \"\"\"Set columns to select. Raise ValueError if any column not in ALLOWED_COLUMNS for this table.\"\"\"

    def where(self, column: str, operator: str, value) -> "SafeQueryBuilder":
        \"\"\"Add a WHERE condition. Only these operators allowed: =, !=, <, >, <=, >=, LIKE, IN.
        Raise ValueError for unknown operators or unknown columns.
        For IN operator, value must be a list/tuple.\"\"\"

    def order_by(self, column: str, direction: str = "ASC") -> "SafeQueryBuilder":
        \"\"\"Add ORDER BY. Raise ValueError if column or direction invalid.\"\"\"

    def limit(self, n: int) -> "SafeQueryBuilder":
        \"\"\"Set LIMIT. Must be positive integer. Raise ValueError otherwise.\"\"\"

    def build(self) -> tuple[str, list]:
        \"\"\"Return (query_string, params) where query_string uses %s placeholders.
        Column and table names are quoted with double quotes.
        Values are always parameterised — never interpolated into the query string.\"\"\"
```

Requirements:
- Table and column names are validated against allowlists, then quoted with double quotes
- Values are ALWAYS parameterised (returned in the params list)
- Operators are validated against the exact allowlist
- ORDER BY direction is validated (only ASC or DESC, case-insensitive)
- LIMIT must be a positive integer, parameterised
- The IN operator should generate the correct number of %s placeholders
"""

# --- Tests (model never sees below this line) ---

import pytest
import importlib


def load():
    mod = importlib.import_module("solutions.c04_security")
    return mod.SafeQueryBuilder


class TestTableValidation:
    """3 points."""

    def test_valid_table(self):
        """(1 pt) Accepted table works."""
        Builder = load()
        b = Builder("users")
        q, p = b.select(["name"]).build()
        assert '"users"' in q

    def test_invalid_table(self):
        """(1 pt) Reject unknown table."""
        Builder = load()
        with pytest.raises(ValueError):
            Builder("admin_secrets")

    def test_sql_injection_in_table(self):
        """(1 pt) Table name with injection attempt is rejected."""
        Builder = load()
        with pytest.raises(ValueError):
            Builder('users"; DROP TABLE users; --')


class TestColumnValidation:
    """2 points."""

    def test_valid_columns(self):
        """(1 pt) Known columns accepted."""
        Builder = load()
        q, p = Builder("users").select(["name", "email"]).build()
        assert '"name"' in q
        assert '"email"' in q

    def test_invalid_column(self):
        """(1 pt) Unknown column rejected."""
        Builder = load()
        with pytest.raises(ValueError):
            Builder("users").select(["password_hash"])


class TestWhereClause:
    """4 points."""

    def test_basic_where(self):
        """(1 pt) Simple equality condition."""
        Builder = load()
        q, p = Builder("users").select(["name"]).where("id", "=", 42).build()
        assert "%s" in q
        assert 42 in p

    def test_injection_in_operator(self):
        """(1 pt) Operator injection attempt rejected."""
        Builder = load()
        with pytest.raises(ValueError):
            Builder("users").select(["name"]).where("id", "= 1 OR 1=1 --", "x").build()

    def test_in_operator(self):
        """(1 pt) IN generates correct placeholders."""
        Builder = load()
        q, p = Builder("orders").select(["id"]).where("status", "IN", ["pending", "shipped"]).build()
        assert q.count("%s") == 2
        assert "pending" in p
        assert "shipped" in p

    def test_injection_in_value(self):
        """(1 pt) Value with SQL is parameterised, not interpolated."""
        Builder = load()
        q, p = Builder("users").select(["name"]).where("name", "=", "'; DROP TABLE users; --").build()
        # The malicious string should be in params, NOT in the query string
        assert "DROP" not in q
        assert "'; DROP TABLE users; --" in p


class TestOrderBy:
    """2 points."""

    def test_valid_order(self):
        """(1 pt) Valid ORDER BY works."""
        Builder = load()
        q, p = Builder("users").select(["name"]).order_by("created_at", "DESC").build()
        assert "ORDER BY" in q
        assert '"created_at"' in q
        assert "DESC" in q

    def test_injection_in_direction(self):
        """(1 pt) Direction injection rejected."""
        Builder = load()
        with pytest.raises(ValueError):
            Builder("users").select(["name"]).order_by("name", "ASC; DROP TABLE users --")


class TestLimit:
    """2 points."""

    def test_valid_limit(self):
        """(1 pt) Positive integer limit works and is parameterised."""
        Builder = load()
        q, p = Builder("users").select(["name"]).limit(10).build()
        assert "LIMIT" in q
        assert 10 in p

    def test_negative_limit(self):
        """(1 pt) Non-positive limit rejected."""
        Builder = load()
        with pytest.raises(ValueError):
            Builder("users").select(["name"]).limit(-1)
        with pytest.raises(ValueError):
            Builder("users").select(["name"]).limit(0)


class TestFullQuery:
    """2 points."""

    def test_complete_query(self):
        """(2 pts) Full query with all clauses assembled correctly."""
        Builder = load()
        q, p = (
            Builder("orders")
            .select(["id", "total", "status"])
            .where("user_id", "=", 7)
            .where("status", "IN", ["pending", "shipped"])
            .order_by("created_at", "DESC")
            .limit(25)
            .build()
        )
        # Should have parameterised values: 7, "pending", "shipped", 25
        assert len(p) == 4
        assert "DROP" not in q
        assert q.count("%s") == 4
