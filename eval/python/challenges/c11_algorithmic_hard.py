"""
CHALLENGE: Dependency Resolver with Cycle Detection
CATEGORY: algorithmic_correctness
DIFFICULTY: 3
POINTS: 15
WHY: Weaker models get topological sort mostly right but fail on: cycles within cycles,
     diamond dependencies, self-dependencies, disconnected subgraphs, and stable ordering.
     They also commonly produce O(n^2) solutions that miss edges, or detect cycles in
     valid DAGs that just have shared nodes (diamond pattern).
"""

PROMPT = """
Write a dependency resolver that determines a valid execution order for tasks.

```python
from dataclasses import dataclass, field

@dataclass
class Task:
    name: str
    depends_on: list[str] = field(default_factory=list)

class CyclicDependencyError(Exception):
    \"\"\"Raised when dependencies form a cycle. The `cycle` attribute contains
    the list of task names forming the cycle, e.g. ["a", "b", "c", "a"].\"\"\"
    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"Cyclic dependency: {' -> '.join(cycle)}")

class MissingDependencyError(Exception):
    \"\"\"Raised when a task depends on a task that doesn't exist.\"\"\"
    def __init__(self, task: str, missing: str):
        self.task = task
        self.missing = missing
        super().__init__(f"Task '{task}' depends on unknown task '{missing}'")

def resolve(tasks: list[Task]) -> list[str]:
    \"\"\"
    Return task names in a valid execution order (dependencies before dependents).

    Rules:
    - If A depends on B, B must appear before A in the output.
    - If multiple valid orderings exist, prefer alphabetical order among tasks
      that are ready at the same time (deterministic output).
    - Raise CyclicDependencyError if there is any cycle. The `cycle` attribute
      must contain the actual cycle path (not just "cycle detected").
    - Raise MissingDependencyError if a task references a dependency that
      is not in the task list.
    - A task depending on itself is a cycle of length 1.
    - Duplicate task names: raise ValueError.
    - Empty input returns empty list.
    \"\"\"
```
"""

# --- Tests (model never sees below this line) ---

import pytest
import importlib


def load():
    mod = importlib.import_module("solutions.c11_algorithmic_hard")
    return mod.resolve, mod.Task, mod.CyclicDependencyError, mod.MissingDependencyError


class TestBasicResolution:
    """3 points."""

    def test_simple_chain(self):
        """(1 pt) A -> B -> C resolves to [C, B, A]."""
        resolve, Task, _, _ = load()
        tasks = [
            Task("a", ["b"]),
            Task("b", ["c"]),
            Task("c"),
        ]
        result = resolve(tasks)
        assert result.index("c") < result.index("b") < result.index("a")

    def test_no_dependencies(self):
        """(1 pt) Independent tasks come out alphabetically."""
        resolve, Task, _, _ = load()
        tasks = [Task("zebra"), Task("apple"), Task("mango")]
        assert resolve(tasks) == ["apple", "mango", "zebra"]

    def test_empty_input(self):
        """(1 pt) Empty list returns empty list."""
        resolve, Task, _, _ = load()
        assert resolve([]) == []


class TestDiamondDependency:
    """3 points — this is where weak models break."""

    def test_diamond(self):
        """(2 pts) Diamond: D depends on B,C; B,C depend on A. No false cycle."""
        resolve, Task, _, _ = load()
        tasks = [
            Task("d", ["b", "c"]),
            Task("b", ["a"]),
            Task("c", ["a"]),
            Task("a"),
        ]
        result = resolve(tasks)
        # A must come first, D must come last, B and C in between (alphabetical)
        assert result[0] == "a"
        assert result[-1] == "d"
        assert result.index("b") < result.index("d")
        assert result.index("c") < result.index("d")

    def test_deep_diamond(self):
        """(1 pt) Multiple diamond convergences don't cause false cycles."""
        resolve, Task, _, _ = load()
        #     f
        #    / \
        #   d   e
        #    \ /
        #     c
        #    / \
        #   a   b
        tasks = [
            Task("f", ["d", "e"]),
            Task("d", ["c"]),
            Task("e", ["c"]),
            Task("c", ["a", "b"]),
            Task("a"),
            Task("b"),
        ]
        result = resolve(tasks)
        assert result.index("a") < result.index("c")
        assert result.index("b") < result.index("c")
        assert result.index("c") < result.index("d")
        assert result.index("c") < result.index("e")
        assert result[-1] == "f"


class TestAlphabeticalStability:
    """2 points."""

    def test_deterministic_ordering(self):
        """(1 pt) Same-level tasks are alphabetical regardless of input order."""
        resolve, Task, _, _ = load()
        # All depend on "root", so order among them should be alphabetical
        tasks = [
            Task("delta", ["root"]),
            Task("alpha", ["root"]),
            Task("charlie", ["root"]),
            Task("bravo", ["root"]),
            Task("root"),
        ]
        result = resolve(tasks)
        assert result[0] == "root"
        assert result[1:] == ["alpha", "bravo", "charlie", "delta"]

    def test_stable_across_runs(self):
        """(1 pt) Running resolve twice gives identical output."""
        resolve, Task, _, _ = load()
        tasks = [Task("c", ["a"]), Task("b", ["a"]), Task("a")]
        r1 = resolve(tasks)
        r2 = resolve(tasks)
        assert r1 == r2


class TestCycleDetection:
    """4 points."""

    def test_simple_cycle(self):
        """(1 pt) A -> B -> A is a cycle."""
        resolve, Task, CyclicError, _ = load()
        tasks = [Task("a", ["b"]), Task("b", ["a"])]
        with pytest.raises(CyclicError) as exc_info:
            resolve(tasks)
        cycle = exc_info.value.cycle
        assert len(cycle) >= 3  # e.g. ["a", "b", "a"]
        assert cycle[0] == cycle[-1]  # Cycle closes

    def test_self_dependency(self):
        """(1 pt) A task depending on itself is a cycle."""
        resolve, Task, CyclicError, _ = load()
        tasks = [Task("a", ["a"])]
        with pytest.raises(CyclicError) as exc_info:
            resolve(tasks)
        cycle = exc_info.value.cycle
        assert "a" in cycle

    def test_long_cycle(self):
        """(1 pt) A -> B -> C -> D -> B (cycle doesn't include all nodes)."""
        resolve, Task, CyclicError, _ = load()
        tasks = [
            Task("a", ["b"]),
            Task("b", ["c"]),
            Task("c", ["d"]),
            Task("d", ["b"]),  # Cycle: B -> C -> D -> B
        ]
        with pytest.raises(CyclicError) as exc_info:
            resolve(tasks)
        cycle = exc_info.value.cycle
        assert cycle[0] == cycle[-1]
        # The cycle should contain b, c, d but not necessarily a
        cycle_set = set(cycle)
        assert {"b", "c", "d"}.issubset(cycle_set)

    def test_cycle_plus_valid_subgraph(self):
        """(1 pt) A valid subgraph coexists with a cyclic one — cycle still detected."""
        resolve, Task, CyclicError, _ = load()
        tasks = [
            Task("x", ["y"]),  # Valid
            Task("y"),         # Valid
            Task("a", ["b"]),  # Cyclic
            Task("b", ["a"]),  # Cyclic
        ]
        with pytest.raises(CyclicError):
            resolve(tasks)


class TestErrorHandling:
    """3 points."""

    def test_missing_dependency(self):
        """(1 pt) Referencing a non-existent task raises MissingDependencyError."""
        resolve, Task, _, MissingError = load()
        tasks = [Task("a", ["nonexistent"])]
        with pytest.raises(MissingError) as exc_info:
            resolve(tasks)
        assert exc_info.value.task == "a"
        assert exc_info.value.missing == "nonexistent"

    def test_duplicate_task_names(self):
        """(1 pt) Duplicate names raise ValueError."""
        resolve, Task, _, _ = load()
        tasks = [Task("a"), Task("a")]
        with pytest.raises(ValueError):
            resolve(tasks)

    def test_disconnected_subgraphs(self):
        """(1 pt) Multiple independent groups all resolve correctly."""
        resolve, Task, _, _ = load()
        tasks = [
            Task("a2", ["a1"]),
            Task("a1"),
            Task("b2", ["b1"]),
            Task("b1"),
        ]
        result = resolve(tasks)
        assert result.index("a1") < result.index("a2")
        assert result.index("b1") < result.index("b2")
        # Alphabetical among same-level: a1 and b1 are both roots
        assert result.index("a1") < result.index("b1")
