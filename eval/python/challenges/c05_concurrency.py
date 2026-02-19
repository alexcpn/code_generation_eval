"""
CHALLENGE: Thread-Safe Rate Limiter
CATEGORY: concurrency
DIFFICULTY: 3
POINTS: 10
WHY: Models generate rate limiters with race conditions — check-then-act without locking,
     time.time() calls outside the lock, or token bucket implementations that go negative.
     Concurrency bugs are the hardest for models to reason about.
"""

PROMPT = """
Write a thread-safe token bucket rate limiter.

```python
import threading
import time

class RateLimiter:
    def __init__(self, rate: float, capacity: int):
        \"\"\"
        Args:
            rate: tokens added per second
            capacity: maximum tokens in the bucket
        The bucket starts full (tokens = capacity).
        \"\"\"

    def acquire(self, tokens: int = 1, timeout: float = 0.0) -> bool:
        \"\"\"
        Try to acquire `tokens` from the bucket.
        - If enough tokens, consume them and return True immediately.
        - If timeout > 0, wait up to `timeout` seconds for tokens to become available.
        - If timeout <= 0, return False immediately if not enough tokens.
        - Must be safe to call from multiple threads simultaneously.
        - tokens must be > 0 and <= capacity, raise ValueError otherwise.
        \"\"\"

    def available(self) -> float:
        \"\"\"Return current number of available tokens (may be fractional). Thread-safe.\"\"\"
```

Requirements:
- Thread-safe: no race conditions under concurrent access
- Tokens refill continuously (not per-interval)
- Bucket never exceeds capacity
- acquire() with timeout blocks efficiently (not busy-wait spin loops)
"""

# --- Tests (model never sees below this line) ---

import pytest
import importlib
import threading
import time


def load():
    mod = importlib.import_module("solutions.c05_concurrency")
    return mod.RateLimiter


class TestBasicBehaviour:
    """4 points."""

    def test_starts_full(self):
        """(1 pt) Bucket starts at capacity."""
        RL = load()
        rl = RL(rate=10, capacity=5)
        assert rl.available() == pytest.approx(5, abs=0.1)

    def test_acquire_reduces_tokens(self):
        """(1 pt) Acquiring tokens reduces availability."""
        RL = load()
        rl = RL(rate=10, capacity=5)
        assert rl.acquire(3) is True
        assert rl.available() == pytest.approx(2, abs=0.1)

    def test_acquire_fails_when_empty(self):
        """(1 pt) Returns False when not enough tokens and no timeout."""
        RL = load()
        rl = RL(rate=1, capacity=2)
        rl.acquire(2)
        assert rl.acquire(1) is False

    def test_tokens_refill(self):
        """(1 pt) Tokens refill over time."""
        RL = load()
        rl = RL(rate=100, capacity=10)
        rl.acquire(10)
        time.sleep(0.05)  # Should refill ~5 tokens at rate=100/sec
        assert rl.available() >= 3  # Allow some timing slack


class TestEdgeCases:
    """2 points."""

    def test_never_exceeds_capacity(self):
        """(1 pt) Even after long wait, tokens don't exceed capacity."""
        RL = load()
        rl = RL(rate=1000, capacity=5)
        time.sleep(0.1)  # Would be 100 tokens at rate=1000, but capped at 5
        assert rl.available() <= 5.0

    def test_invalid_acquire(self):
        """(1 pt) ValueError for tokens <= 0 or > capacity."""
        RL = load()
        rl = RL(rate=10, capacity=5)
        with pytest.raises(ValueError):
            rl.acquire(0)
        with pytest.raises(ValueError):
            rl.acquire(6)


class TestConcurrency:
    """4 points."""

    def test_no_overdraft(self):
        """(2 pts) Multiple threads cannot overdraft the bucket."""
        RL = load()
        rl = RL(rate=0, capacity=100)  # rate=0 means no refill
        success_count = {"n": 0}
        lock = threading.Lock()

        def try_acquire():
            if rl.acquire(1):
                with lock:
                    success_count["n"] += 1

        threads = [threading.Thread(target=try_acquire) for _ in range(200)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 100 should succeed (bucket started with 100, no refill)
        assert success_count["n"] == 100

    def test_timeout_works(self):
        """(1 pt) acquire with timeout waits for refill."""
        RL = load()
        rl = RL(rate=100, capacity=5)
        rl.acquire(5)  # Drain it
        # With timeout=0.1, should refill ~10 tokens, so acquiring 1 should work
        assert rl.acquire(1, timeout=0.2) is True

    def test_timeout_expires(self):
        """(1 pt) acquire returns False when timeout expires without enough tokens."""
        RL = load()
        rl = RL(rate=1, capacity=10)
        rl.acquire(10)  # Drain it
        start = time.time()
        result = rl.acquire(5, timeout=0.1)  # Need 5 tokens, only ~0.1 will refill
        elapsed = time.time() - start
        assert result is False
        assert elapsed >= 0.09  # Should have waited roughly the timeout
