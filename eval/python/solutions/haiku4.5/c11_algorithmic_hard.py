from dataclasses import dataclass, field
from typing import Optional

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
    - Raise MissingDependencyError if a task references a dependency that
      is not in the task list.
    - A task depending on itself is a cycle of length 1.
    - Duplicate task names: raise ValueError.
    - Empty input returns empty list.
    """
    if not tasks:
        return []
    
    # Check for duplicate task names
    task_names = [task.name for task in tasks]
    if len(task_names) != len(set(task_names)):
        duplicates = [name for name in task_names if task_names.count(name) > 1]
        raise ValueError(f"Duplicate task names: {duplicates}")
    
    task_dict = {task.name: task for task in tasks}
    
    # Validate all dependencies exist
    for task in tasks:
        for dep in task.depends_on:
            if dep not in task_dict:
                raise MissingDependencyError(task.name, dep)
    
    # Kahn's algorithm with cycle detection
    # Build in-degree map and adjacency list
    in_degree = {task.name: 0 for task in tasks}
    adjacency = {task.name: [] for task in tasks}
    
    for task in tasks:
        for dep in task.depends_on:
            # dep -> task (task depends on dep, so dep must come before)
            adjacency[dep].append(task.name)
            in_degree[task.name] += 1
    
    # Find all nodes with in_degree 0 (no dependencies)
    queue = sorted([name for name in in_degree if in_degree[name] == 0])
    result = []
    
    while queue:
        # Process in sorted order for deterministic output
        queue.sort()
        current = queue.pop(0)
        result.append(current)
        
        # Reduce in_degree of neighbors
        for neighbor in adjacency[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # Check if all tasks were processed (cycle detection)
    if len(result) != len(tasks):
        # Find the cycle using DFS
        cycle = _find_cycle(task_dict, adjacency)
        raise CyclicDependencyError(cycle)
    
    return result


def _find_cycle(task_dict: dict, adjacency: dict) -> list[str]:
    """
    Find and return a cycle in the dependency graph using DFS.
    Returns the cycle as a list of task names ending with the repeated node.
    """
    # States: 0 = unvisited, 1 = visiting, 2 = visited
    state = {name: 0 for name in task_dict}
    path = []
    
    def dfs(node: str) -> Optional[list[str]]:
        if state[node] == 1:
            # Found a cycle: backtrack from path to find the start
            cycle_start_idx = path.index(node)
            return path[cycle_start_idx:] + [node]
        
        if state[node] == 2:
            # Already fully explored
            return None
        
        state[node] = 1
        path.append(node)
        
        for neighbor in adjacency[node]:
            cycle = dfs(neighbor)
            if cycle:
                return cycle
        
        path.pop()
        state[node] = 2
        return None
    
    # Try starting DFS from each unvisited node
    for task_name in task_dict:
        if state[task_name] == 0:
            cycle = dfs(task_name)
            if cycle:
                return cycle
    
    # Should not reach here if caller verified a cycle exists
    return []
