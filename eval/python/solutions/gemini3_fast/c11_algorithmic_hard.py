import heapq

def resolve(tasks: list[Task]) -> list[str]:
    if not tasks:
        return []

    # 1. Build the graph and check for duplicate names
    adj = {}
    in_degree = {}
    all_task_names = set()
    
    for task in tasks:
        if task.name in all_task_names:
            raise ValueError(f"Duplicate task name: {task.name}")
        all_task_names.add(task.name)
        adj[task.name] = []
        in_degree[task.name] = 0

    # 2. Map dependencies and check for MissingDependencyError
    for task in tasks:
        for dep in task.depends_on:
            if dep not in all_task_names:
                raise MissingDependencyError(task.name, dep)
            
            # The edge goes from Dependency -> Task (to track "readiness")
            adj[dep].append(task.name)
            in_degree[task.name] += 1

    # 3. Cycle Detection with Path (DFS)
    # We do this to specifically fulfill the CyclicDependencyError requirements
    visited = {} # 0: unvisited, 1: visiting, 2: visited
    
    def find_cycle(u, path):
        visited[u] = 1
        path.append(u)
        for v in [t.depends_on for t in tasks if t.name == u][0]:
            if visited.get(v, 0) == 1:
                # Cycle found! Extract the relevant portion of the path
                cycle_start_idx = path.index(v)
                raise CyclicDependencyError(path[cycle_start_idx:] + [v])
            if visited.get(v, 0) == 0:
                find_cycle(v, path)
        path.pop()
        visited[u] = 2

    for name in all_task_names:
        if visited.get(name, 0) == 0:
            find_cycle(name, [])

    # 4. Kahn's Algorithm with a Heap for Deterministic Order
    # Start with tasks that have 0 dependencies
    ready_queue = [name for name in all_task_names if in_degree[name] == 0]
    heapq.heapify(ready_queue)
    
    execution_order = []
    
    while ready_queue:
        current = heapq.heappop(ready_queue)
        execution_order.append(current)
        
        for neighbor in adj[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                heapq.heappush(ready_queue, neighbor)

    return execution_order