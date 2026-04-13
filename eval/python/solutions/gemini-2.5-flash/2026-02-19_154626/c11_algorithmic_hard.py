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