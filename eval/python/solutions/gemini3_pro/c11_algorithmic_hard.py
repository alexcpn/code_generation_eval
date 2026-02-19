import heapq
from dataclasses import dataclass, field

@dataclass
class Task:
    name: str
    depends_on: list[str] = field(default_factory=list)

class CyclicDependencyError(Exception):
    """Raised when dependencies form a cycle."""
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
    Return task names in a valid execution order.
    Dependencies are processed before dependents, with deterministic 
    alphabetical ordering for ties.
    """
    if not tasks:
        return []

    task_dict = {}
    for t in tasks:
        if t.name in task_dict:
            raise ValueError(f"Duplicate task name: {t.name}")
        task_dict[t.name] = t

    # Initialize graph structures
    adj = {t.name: [] for t in tasks}
    in_degree = {t.name: 0 for t in tasks}

    # Build the directed graph and validate missing dependencies
    for t in tasks:
        for dep in t.depends_on:
            if dep not in task_dict:
                raise MissingDependencyError(t.name, dep)
            # Edge points from dependency -> dependent
            adj[dep].append(t.name)
            in_degree[t.name] += 1

    # Initialize a min-heap with tasks that have no dependencies
    ready = [name for name, deg in in_degree.items() if deg == 0]
    heapq.heapify(ready)

    result = []
    
    # Process tasks
    while ready:
        curr = heapq.heappop(ready)
        result.append(curr)
        for dependent in adj[curr]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                heapq.heappush(ready, dependent)

    # If the result length doesn't match task count, we have a cycle
    if len(result) < len(tasks):
        # Isolate the remaining nodes involved in the cycle(s)
        remaining = {name for name, deg in in_degree.items() if deg > 0}
        visited = set()

        def find_cycle(node: str, path: list[str]) -> list[str] | None:
            if node in path:
                # Cycle detected: slice the path to return the actual loop
                idx = path.index(node)
                return path[idx:] + [node]
            if node in visited:
                return None

            visited.add(node)
            path.append(node)

            # Follow dependencies backward to trace the cycle root
            for dep in task_dict[node].depends_on:
                if dep in remaining:
                    cycle = find_cycle(dep, path)
                    if cycle:
                        return cycle

            path.pop()
            return None

        # Trace the exact cycle path for the error
        for node in remaining:
            cycle = find_cycle(node, [])
            if cycle:
                raise CyclicDependencyError(cycle)

    return result