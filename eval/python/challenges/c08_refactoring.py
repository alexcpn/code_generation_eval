"""
CHALLENGE: Refactor Without Breaking
CATEGORY: refactoring
DIFFICULTY: 2
POINTS: 10
WHY: Models rewrite instead of refactoring. When asked to improve code, they change
     behaviour, rename public APIs, or "simplify" by removing edge case handling.
     This challenge gives bad code with a full test suite and asks the model to improve
     it WITHOUT breaking any tests.
"""

PROMPT = """
The following code works and passes all its tests, but it's poorly written.
Refactor it to improve readability, maintainability, and design — WITHOUT changing
any public function signatures or observable behaviour.

Rules:
- Do NOT rename any public functions or change their parameters
- Do NOT change what the functions return for any input
- DO extract helper functions, rename internal variables, remove duplication
- DO improve the structure, but keep all edge case handling intact

```python
def proc(d, t):
    r = []
    if d is None or len(d) == 0:
        return r
    for i in range(len(d)):
        x = d[i]
        if t == "upper":
            if x is not None and isinstance(x, str):
                r.append(x.upper())
            elif x is not None and isinstance(x, (int, float)):
                r.append(str(x).upper())
            else:
                r.append("")
        elif t == "lower":
            if x is not None and isinstance(x, str):
                r.append(x.lower())
            elif x is not None and isinstance(x, (int, float)):
                r.append(str(x).lower())
            else:
                r.append("")
        elif t == "title":
            if x is not None and isinstance(x, str):
                r.append(x.title())
            elif x is not None and isinstance(x, (int, float)):
                r.append(str(x).title())
            else:
                r.append("")
        elif t == "len":
            if x is not None and isinstance(x, str):
                r.append(len(x))
            elif x is not None and isinstance(x, (int, float)):
                r.append(len(str(x)))
            else:
                r.append(0)
        else:
            r.append(x)
    return r


def merge(a, b, k):
    r = {}
    if a is None:
        a = {}
    if b is None:
        b = {}
    for key in a:
        if key in b:
            if k == "keep_first":
                r[key] = a[key]
            elif k == "keep_last":
                r[key] = b[key]
            elif k == "combine":
                if isinstance(a[key], list) and isinstance(b[key], list):
                    r[key] = a[key] + b[key]
                elif isinstance(a[key], list):
                    r[key] = a[key] + [b[key]]
                elif isinstance(b[key], list):
                    r[key] = [a[key]] + b[key]
                else:
                    r[key] = [a[key], b[key]]
            else:
                r[key] = a[key]
        else:
            r[key] = a[key]
    for key in b:
        if key not in a:
            r[key] = b[key]
    return r
```

Return the refactored code. Both functions `proc` and `merge` must remain with exactly
those names and signatures.
"""

# --- Tests (model never sees below this line) ---

import pytest
import importlib


def load():
    mod = importlib.import_module("solutions.c08_refactoring")
    return mod.proc, mod.merge


class TestProcBehaviourPreserved:
    """5 points."""

    def test_upper_transform(self):
        """(1 pt) Upper transform on strings."""
        proc, _ = load()
        assert proc(["hello", "World"], "upper") == ["HELLO", "WORLD"]

    def test_lower_transform(self):
        """(1 pt) Lower transform on strings."""
        proc, _ = load()
        assert proc(["HELLO", "World"], "lower") == ["hello", "world"]

    def test_mixed_types(self):
        """(1 pt) Numbers are converted to string before transform."""
        proc, _ = load()
        assert proc([42, 3.14, "hi"], "upper") == ["42", "3.14", "HI"]

    def test_none_and_empty(self):
        """(1 pt) None items become empty string, None/empty input returns []."""
        proc, _ = load()
        assert proc([None, "a"], "upper") == ["", "A"]
        assert proc(None, "upper") == []
        assert proc([], "upper") == []

    def test_len_transform(self):
        """(1 pt) Len transform returns lengths."""
        proc, _ = load()
        assert proc(["hi", "hello", 42, None], "len") == [2, 5, 2, 0]


class TestMergeBehaviourPreserved:
    """3 points."""

    def test_keep_first(self):
        """(1 pt) keep_first strategy."""
        _, merge = load()
        result = merge({"a": 1, "b": 2}, {"b": 3, "c": 4}, "keep_first")
        assert result == {"a": 1, "b": 2, "c": 4}

    def test_keep_last(self):
        """(1 pt) keep_last strategy."""
        _, merge = load()
        result = merge({"a": 1, "b": 2}, {"b": 3, "c": 4}, "keep_last")
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_combine(self):
        """(1 pt) combine strategy — all variations."""
        _, merge = load()
        # Both lists
        assert merge({"a": [1]}, {"a": [2]}, "combine") == {"a": [1, 2]}
        # First is list
        assert merge({"a": [1]}, {"a": 2}, "combine") == {"a": [1, 2]}
        # Second is list
        assert merge({"a": 1}, {"a": [2]}, "combine") == {"a": [1, 2]}
        # Neither is list
        assert merge({"a": 1}, {"a": 2}, "combine") == {"a": [1, 2]}


class TestRefactoringQuality:
    """2 points."""

    def test_no_range_len_pattern(self):
        """(1 pt) Refactored code should not use for i in range(len(...))."""
        proc, _ = load()
        import inspect

        source = inspect.getsource(proc)
        assert "range(len" not in source, "Should iterate directly, not with range(len())"

    def test_reduced_duplication(self):
        """(1 pt) Refactored proc should have less duplication (shorter source)."""
        proc, _ = load()
        import inspect

        source = inspect.getsource(proc)
        # The original has 4 near-identical blocks. A good refactoring should be much shorter.
        # Original is ~40 lines. A good refactoring should be under 25.
        line_count = len([l for l in source.strip().split("\n") if l.strip()])
        assert line_count < 30, f"Code has {line_count} lines — still too much duplication"
