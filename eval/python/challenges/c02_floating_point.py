"""
CHALLENGE: Money Arithmetic
CATEGORY: algorithmic_correctness
DIFFICULTY: 2
POINTS: 12
WHY: Models use float for money calculations. This causes rounding errors that accumulate
     in production and create accounting discrepancies. The correct approach is Decimal or
     integer-cents. Most models get this wrong on the first attempt.
"""

PROMPT = """
Write a class `MoneyLedger` for tracking financial transactions with exact precision.

```python
class MoneyLedger:
    def __init__(self, currency: str = "USD"):
        ...

    def add_transaction(self, description: str, amount: str) -> None:
        \"\"\"Add a transaction. Amount is a string like "19.99" or "-5.50".
        Raises ValueError if amount has more than 2 decimal places.\"\"\"

    def balance(self) -> str:
        \"\"\"Return current balance as a string with exactly 2 decimal places. e.g. "14.49" \"\"\"

    def apply_percentage(self, description: str, percentage: str) -> None:
        \"\"\"Apply a percentage to the current balance and add as a new transaction.
        e.g. apply_percentage("tax", "8.25") adds 8.25% of current balance.
        Result is rounded to 2 decimal places using ROUND_HALF_UP.\"\"\"

    def statement(self) -> list[dict]:
        \"\"\"Return list of {"description": str, "amount": str, "running_balance": str}.\"\"\"
```

Requirements:
- All arithmetic must be exact — no floating point errors
- Amounts are always strings with 2 decimal places in output
- Negative balances are allowed
- apply_percentage on zero balance adds "0.00"
"""

# --- Tests (model never sees below this line) ---

import pytest
import importlib


def load():
    mod = importlib.import_module("solutions.c02_floating_point")
    return mod.MoneyLedger


class TestMoneyLedger:
    """12 points total."""

    def test_basic_transactions(self):
        """(1 pt) Simple add and balance."""
        Ledger = load()
        ledger = Ledger()
        ledger.add_transaction("deposit", "100.00")
        assert ledger.balance() == "100.00"

    def test_negative_transaction(self):
        """(1 pt) Negative amounts reduce balance."""
        Ledger = load()
        ledger = Ledger()
        ledger.add_transaction("deposit", "50.00")
        ledger.add_transaction("withdrawal", "-30.00")
        assert ledger.balance() == "20.00"

    def test_classic_float_trap(self):
        """(2 pts) 0.1 + 0.2 != 0.3 in float. This must be exact."""
        Ledger = load()
        ledger = Ledger()
        ledger.add_transaction("a", "0.10")
        ledger.add_transaction("b", "0.20")
        assert ledger.balance() == "0.30"  # float would give 0.30000000000000004

    def test_accumulation_error(self):
        """(2 pts) Adding 0.01 one hundred times must equal 1.00 exactly."""
        Ledger = load()
        ledger = Ledger()
        for i in range(100):
            ledger.add_transaction(f"penny_{i}", "0.01")
        assert ledger.balance() == "1.00"

    def test_percentage_calculation(self):
        """(2 pts) 8.25% of $100.00 = $8.25."""
        Ledger = load()
        ledger = Ledger()
        ledger.add_transaction("sale", "100.00")
        ledger.apply_percentage("tax", "8.25")
        assert ledger.balance() == "108.25"

    def test_percentage_rounding(self):
        """(2 pts) 33.33% of $100.00 = $33.33 (ROUND_HALF_UP)."""
        Ledger = load()
        ledger = Ledger()
        ledger.add_transaction("deposit", "100.00")
        ledger.apply_percentage("fee", "33.33")
        # 33.33% of 100 = 33.33, balance = 133.33
        assert ledger.balance() == "133.33"

    def test_percentage_half_up_rounding(self):
        """(1 pt) ROUND_HALF_UP: 2.5% of $10.01 = 0.25025 -> 0.25."""
        Ledger = load()
        ledger = Ledger()
        ledger.add_transaction("deposit", "10.01")
        ledger.apply_percentage("interest", "2.50")
        # 2.5% of 10.01 = 0.25025 -> rounds to 0.25
        assert ledger.balance() == "10.26"

    def test_invalid_precision(self):
        """(1 pt) Reject amounts with more than 2 decimal places."""
        Ledger = load()
        ledger = Ledger()
        with pytest.raises(ValueError):
            ledger.add_transaction("bad", "1.999")

    def test_statement_running_balance(self):
        """(1 pt) Statement shows running balance after each transaction."""
        Ledger = load()
        ledger = Ledger()
        ledger.add_transaction("deposit", "100.00")
        ledger.add_transaction("spend", "-40.50")
        stmt = ledger.statement()
        assert len(stmt) == 2
        assert stmt[0]["running_balance"] == "100.00"
        assert stmt[1]["running_balance"] == "59.50"

    def test_zero_balance_percentage(self):
        """(1 pt) Percentage on zero balance adds 0.00."""
        Ledger = load()
        ledger = Ledger()
        ledger.apply_percentage("tax on nothing", "15.00")
        assert ledger.balance() == "0.00"
