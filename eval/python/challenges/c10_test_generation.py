"""
CHALLENGE: Bug-Finding Test Generation
CATEGORY: algorithmic_correctness
DIFFICULTY: 3
POINTS: 10
WHY: This is the meta-challenge. Models generate tests that only cover the happy path.
     Here we give the model a function WITH a planted subtle bug and ask it to write
     tests. A good model will write a test that catches the bug. A weak model will
     write tests that all pass on the buggy code.
"""

PROMPT = """
The following function claims to find the longest substring without repeating characters.
Write at least 8 comprehensive unit tests for it. Your tests should cover:
- Normal cases
- Edge cases (empty string, single char, all same chars)
- Unicode characters
- The test should verify both the length AND the actual substring returned

```python
def longest_unique_substring(s: str) -> tuple[str, int]:
    \"\"\"
    Find the longest substring without repeating characters.
    Returns (substring, length).
    If there are ties, return the first one found.
    If the string is empty, return ("", 0).
    \"\"\"
    if not s:
        return ("", 0)

    start = 0
    max_start = 0
    max_length = 0
    seen = {}

    for end in range(len(s)):
        if s[end] in seen and seen[s[end]] >= start:
            start = seen[s[end]] + 1
        seen[s[end]] = end
        if end - start + 1 >= max_length:  # BUG: should be > not >=
            max_length = end - start + 1
            max_start = start

    return (s[max_start:max_start + max_length], max_length)
```

Write tests using pytest. Import the function as:
`from solutions.c10_test_generation import longest_unique_substring`
"""

# --- Tests (model never sees below this line) ---
# Here we test the MODEL'S TESTS, not the function itself.
# We run the model's tests against both the BUGGY and FIXED versions.
# Good tests should PASS on the fixed version and at least one should FAIL on the buggy version.

import pytest
import importlib
import subprocess
import sys
import os
import tempfile


# The BUGGY version (same as in the prompt)
BUGGY_CODE = '''
def longest_unique_substring(s: str) -> tuple[str, int]:
    if not s:
        return ("", 0)
    start = 0
    max_start = 0
    max_length = 0
    seen = {}
    for end in range(len(s)):
        if s[end] in seen and seen[s[end]] >= start:
            start = seen[s[end]] + 1
        seen[s[end]] = end
        if end - start + 1 >= max_length:  # BUG: >= instead of >
            max_length = end - start + 1
            max_start = start
    return (s[max_start:max_start + max_length], max_length)
'''

# The FIXED version
FIXED_CODE = '''
def longest_unique_substring(s: str) -> tuple[str, int]:
    if not s:
        return ("", 0)
    start = 0
    max_start = 0
    max_length = 0
    seen = {}
    for end in range(len(s)):
        if s[end] in seen and seen[s[end]] >= start:
            start = seen[s[end]] + 1
        seen[s[end]] = end
        if end - start + 1 > max_length:  # FIXED: > instead of >=
            max_length = end - start + 1
            max_start = start
    return (s[max_start:max_start + max_length], max_length)
'''


def _run_tests_against(impl_code: str, test_file: str) -> tuple[int, int]:
    """Run the model's test file against a given implementation. Returns (passed, failed)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write the implementation
        sol_dir = os.path.join(tmpdir, "solutions")
        os.makedirs(sol_dir)
        with open(os.path.join(sol_dir, "__init__.py"), "w") as f:
            f.write("")
        with open(os.path.join(sol_dir, "c10_test_generation.py"), "w") as f:
            f.write(impl_code)

        # Copy the model's test file
        with open(test_file, "r") as f:
            test_code = f.read()
        test_path = os.path.join(tmpdir, "test_model.py")
        with open(test_path, "w") as f:
            f.write(test_code)

        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-v", "--tb=no", "-q"],
            capture_output=True, text=True, cwd=tmpdir, timeout=30
        )

        # Parse pytest output for pass/fail counts
        passed = failed = 0
        for line in result.stdout.split("\n"):
            if "passed" in line:
                import re
                m = re.search(r"(\d+) passed", line)
                if m:
                    passed = int(m.group(1))
            if "failed" in line:
                import re
                m = re.search(r"(\d+) failed", line)
                if m:
                    failed = int(m.group(1))
        return passed, failed


class TestModelTests:
    """10 points total."""

    def _get_test_file(self):
        """Get the model's test file path."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "solutions", "c10_test_generation.py"
        )
        assert os.path.exists(path), "Solution file not found"
        return path

    def test_tests_exist_and_run(self):
        """(2 pts) Model wrote tests that actually run (no syntax errors)."""
        test_file = self._get_test_file()
        passed, failed = _run_tests_against(FIXED_CODE, test_file)
        assert passed + failed > 0, "No tests found or all errored"

    def test_minimum_test_count(self):
        """(2 pts) At least 8 test cases as requested."""
        test_file = self._get_test_file()
        passed, failed = _run_tests_against(FIXED_CODE, test_file)
        assert passed + failed >= 8, f"Only {passed + failed} tests, need at least 8"

    def test_all_pass_on_fixed(self):
        """(2 pts) All model tests pass on the correct implementation."""
        test_file = self._get_test_file()
        passed, failed = _run_tests_against(FIXED_CODE, test_file)
        assert failed == 0, f"{failed} tests fail on correct implementation"

    def test_catches_bug(self):
        """(4 pts) At least one model test fails on the buggy implementation.
        This is the key test: did the model write tests good enough to catch the >= vs > bug?
        The bug causes the function to return the LAST tied substring instead of the FIRST.
        e.g., 'abcabc' should return 'abc' (first), buggy returns 'cab' or 'bca' (last tied).
        """
        test_file = self._get_test_file()
        passed, failed = _run_tests_against(BUGGY_CODE, test_file)
        assert failed > 0, (
            "Model's tests all pass on buggy code — tests are not good enough to catch the bug. "
            "The bug: >= instead of > means ties return the LAST match instead of FIRST."
        )
