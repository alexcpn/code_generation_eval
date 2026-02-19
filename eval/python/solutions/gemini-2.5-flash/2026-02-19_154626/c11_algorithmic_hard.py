from dataclasses import dataclass, field
import collections

@dataclass
class Task:
    name: str
    depends_on: list[str] = field(default_factory=list)

class CyclicDependencyError(Exception):
    """Raised when dependencies form a cycle. The `cycle` attribute contains
    the list of task names forming the cycle, e.g. ["a", "b", "c", "a"]."""
    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"Cyclic dependency: {' -> '.join(cycle)}")

class MissingDependencyError(Exception):
    """Raised when a task depends on a task that doesn't exist."""
    def __init__(self, task: str, missing: str):
        self.task = task
        self.missing = missing
        super().__init__(f"Task '{task}' depends on unknown task '{missing}'")

def resolve(tasks: list[Task]) -> list[str]:
    """
    Return task names in a valid execution order (dependencies before dependents).

    Rules:
    - If A depends on B, B must appear before A in the output.
    - If multiple valid orderings exist, prefer alphabetical order among tasks
      that are ready at the same time (deterministic output).
    - Raise CyclicDependencyError if there is any cycle. The `cycle` attribute
      must contain the actual cycle path (not just "cycle detected").