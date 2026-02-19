from dependency_resolver import Task, resolve, CyclicDependencyError, MissingDependencyError

def test_basic_dependency():
    tasks = [
        Task('build', depends_on=['compile']),
        Task('compile', depends_on=['clean']),
        Task('clean', depends_on=[]),
        Task('test', depends_on=['build'])
    ]
    order = resolve(tasks)
    assert order == ['clean', 'compile', 'build', 'test'], f"Incorrect order: {order}"
    print("Basic dependency test passed")

def test_alphabetical_order():
    tasks = [
        Task('b', depends_on=['a']),
        Task('a', depends_on=[]),
        Task('c', depends_on=['a'])
    ]
    order = resolve(tasks)
    assert order == ['a', 'b', 'c'], f"Incorrect order: {order}"
    print("Alphabetical order test passed")

def test_self_dependency():
    try:
        tasks = [Task('a', depends_on=['a'])]
        resolve(tasks)
        assert False, "Should raise CyclicDependencyError"
    except CyclicDependencyError as e:
        assert e.cycle == ['a', 'a'], "Incorrect cycle detected"
        print("Self-dependency test passed")

def test_complex_cycle():
    try:
        tasks = [
            Task('a', depends_on=['b']),
            Task('b', depends_on=['c']),
            Task('c', depends_on=['a'])
        ]
        resolve(tasks)
        assert False, "Should raise CyclicDependencyError"
    except CyclicDependencyError as e:
        assert set(e.cycle) == {'a', 'b', 'c'}, "Incorrect cycle detected"
        print("Complex cycle test passed")

def test_missing_dependency():
    try:
        tasks = [Task('a', depends_on=['nonexistent'])]
        resolve(tasks)
        assert False, "Should raise MissingDependencyError"
    except MissingDependencyError as e:
        assert e.task == 'a' and e.missing == 'nonexistent'
        print("Missing dependency test passed")

def test_duplicate_tasks():
    try:
        tasks = [
            Task('a', depends_on=[]),
            Task('a', depends_on=[])
        ]
        resolve(tasks)
        assert False, "Should raise ValueError"
    except ValueError:
        print("Duplicate tasks test passed")

def test_empty_input():
    assert resolve([]) == [], "Empty input should return empty list"
    print("Empty input test passed")

def main():
    test_basic_dependency()
    test_alphabetical_order()
    test_self_dependency()
    test_complex_cycle()
    test_missing_dependency()
    test_duplicate_tasks()
    test_empty_input()
    print("All tests passed!")

if __name__ == '__main__':
    main()
