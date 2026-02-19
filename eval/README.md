# AI Code Generation Eval

A practical benchmark for measuring how well an AI model generates production-quality code.

## Philosophy

Most AI benchmarks test whether code *runs*. This eval tests whether code is **correct at the edges, secure by default, well-designed, and maintainable** — the things that separate a demo from production.

Each challenge targets a specific failure mode that real AI models exhibit. The challenges are calibrated so that:
- State-of-the-art models (Opus-class) score **90-100**
- Strong models (Sonnet-class) score **75-85**
- Mid-tier models score **55-70**
- Weak models score **below 50**

The score tells you: *"Can I trust this model for this category of work?"*

## Quick Start

```bash
cd eval/python
pip install pyyaml anthropic openai google-genai   # install what you need

# Set API keys for the providers you want to test
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GOOGLE_API_KEY=AI...

# Run one model
python run_eval.py --auto --model claude-sonnet

# Run all configured models
python run_eval.py --auto

# Compare results side-by-side
python run_eval.py --compare
```

## Modes

### Auto Mode (recommended)
Sends prompts to model APIs automatically, saves solutions, scores them.

```bash
python run_eval.py --auto                                    # All models
python run_eval.py --auto --model claude-opus                # One model
python run_eval.py --auto --model gpt-4o -c c01_off_by_one  # One model, one challenge

python run_eval.py --auto --model gemini-2.5-flash -c c01_off_by_one
python run_eval.py --auto --rerun                            # Ignore cached solutions
```

Solutions are cached in `results/<model_name>/solutions/`.

Example

Models https://ai.google.dev/gemini-api/docs/models Add in eval_config.yaml

Get your Gemini key from https://aistudio.google.com/app/api-keys

export GOOGLE_API_KEY=xxx ()

`$ python3 run_eval.py --auto --model gemini-2.5-flash -c c01_off_by_one`

```
  Model: gemini-2.5-flash (openai/gemini-2.5-flash)
  Output: solutions/gemini-2.5-flash/2026-02-19_154446/
  ───────────────────────────────────────────────────────
  c01_off_by_one: querying gemini-2.5-flash... (16.4s) -> [PASS] 8.0/8

============================================================
  AI CODE GENERATION EVAL — Python — gemini-2.5-flash/2026-02-19_154446
============================================================

  Category                          Score    Pct
  ────────────────────────────────────────────────
  Algorithmic Correctness         8.0/8     100%
  ────────────────────────────────────────────────
  TOTAL                           8.0/8     100%

  Model tier: Opus-class (state of the art)

  Re-score: python3 run_eval.py --score -c gemini-2.5-flash/2026-02-19_154446
```

`$ python3 run_eval.py --auto --model gemini-2.5-flash -c c11_algorithmic_hard`

```
  Model: gemini-2.5-flash (openai/gemini-2.5-flash)
  Output: solutions/gemini-2.5-flash/2026-02-19_154626/
  ───────────────────────────────────────────────────────
  c11_algorithmic_hard: querying gemini-2.5-flash... (35.0s) -> [PARTIAL] 0.0/15

============================================================
  AI CODE GENERATION EVAL — Python — gemini-2.5-flash/2026-02-19_154626
============================================================

  Category                          Score    Pct
  ────────────────────────────────────────────────
  Algorithmic Correctness         0.0/15      0%
  ────────────────────────────────────────────────
  TOTAL                           0.0/15      0%

  Weaknesses:
    - Algorithmic Correctness: c11_algorithmic_hard (0/14 tests passed)

  Model tier: Below mid-tier — review AI output carefully

  Re-score: python3 run_eval.py --score -c gemini-2.5-flash/2026-02-19_154626
```


### Manual Mode
For models without API access (e.g., Claude Code, Cursor, ChatGPT web).

```bash
python run_eval.py --prompts                    # Print all prompts
python run_eval.py --prompt c01_off_by_one      # Print one prompt

# Paste each prompt into your AI tool, save response to:
#   solutions/<challenge_name>.py

python run_eval.py --score                      # Score all solutions
python run_eval.py --score -c c01_off_by_one    # Score one
```

### Compare Mode
After running multiple models, compare them side-by-side:

```bash
python run_eval.py --compare
```

Output:
```
  MODEL COMPARISON

  Challenge                   claude-opus  gpt-4o  gemini-2.5-pro
  ─────────────────────────────────────────────────────────────────
  c01_off_by_one                    8/8     8/8           7/8
  c02_floating_point               12/12    8/12         10/12
  c04_security                     15/15   13/15         12/15
  ...
  ─────────────────────────────────────────────────────────────────
  TOTAL                        98/110(89%) 82/110(75%)  78/110(71%)

  BY CATEGORY
  Algorithmic Correctness          95%      75%          80%
  Security                        100%      87%          80%
  Concurrency                      80%      60%          50%
  ...
```

## Configuration — eval_config.yaml

```yaml
system_prompt: |
  You are a senior Python developer. Return ONLY Python code.

models:
  claude-opus:
    provider: anthropic
    model: claude-opus-4-6
    api_key_env: ANTHROPIC_API_KEY   # reads from env var
    temperature: 0.0
    max_tokens: 4096

  gpt-4o:
    provider: openai
    model: gpt-4o
    api_key_env: OPENAI_API_KEY

  gemini-2.5-pro:
    provider: google
    model: gemini-2.5-pro-preview-06-05
    api_key_env: GOOGLE_API_KEY

  # OpenAI-compatible APIs (DeepSeek, Together, etc.)
  deepseek-v3:
    provider: openai
    model: deepseek-chat
    api_key_env: DEEPSEEK_API_KEY
    api_base: https://api.deepseek.com/v1
```

**Supported providers:** `anthropic`, `openai` (+ any OpenAI-compatible API via `api_base`), `google`

## File Structure

```
eval/
  README.md
  python/
    eval_config.yaml         # Model definitions and API keys
    run_eval.py              # Runner (auto, manual, compare)
    providers.py             # Provider abstraction (Anthropic, OpenAI, Google)
    challenges/
      c01_off_by_one.py      # Pagination boundary math (8 pts)
      c02_floating_point.py  # Money arithmetic — float trap (12 pts)
      c03_edge_cases.py      # Unicode, grapheme-safe truncation (10 pts)
      c04_security.py        # SQL injection — 5 attack surfaces (15 pts)
      c05_concurrency.py     # Thread-safe rate limiter (10 pts)
      c06_error_handling.py  # Resilient HTTP client (10 pts)
      c07_design_solid.py    # Notification system — OCP (20 pts)
      c08_refactoring.py     # Refactor without breaking (10 pts)
      c09_edge_boundaries.py # Date/time with DST (5 pts)
      c10_test_generation.py # META: can it find a planted bug? (10 pts)
    solutions/               # Manual mode solutions go here
    results/                 # Auto mode: per-model solutions + scores
      claude-opus/
        solutions/           # Generated code
        results.json         # Structured scores
      gpt-4o/
        ...
```

## Challenge Anatomy

Each challenge file defines:
- **PROMPT**: the exact text sent to the model (model never sees the tests)
- **Tests**: pytest functions that validate correctness, design, security
- **Metadata**: category, difficulty, points, and WHY models fail at this

## Scoring

- **Partial credit**: 4/5 edge cases handled = 4/5 of the points
- **No style points**: formatting doesn't affect score
- **Behaviour only**: tests check *what*, not *how* — unless design is the challenge
- **Security is binary**: a vulnerability is 0 points, not partial

## Adding Challenges

Create `challenges/c<NN>_<name>.py`:

```python
"""
CHALLENGE: <name>
CATEGORY: <algorithmic_correctness|edge_cases|security|concurrency|error_handling|design_solid|refactoring>
DIFFICULTY: <1-3>
POINTS: <total>
WHY: <why models fail at this>
"""

PROMPT = """
<Exact text sent to the model. Self-contained. No references to other files.>
"""

# --- Tests (model never sees below this line) ---
import pytest
import importlib

def load():
    mod = importlib.import_module("solutions.c<NN>_<name>")
    return mod.<function_or_class>

class TestChallenge:
    def test_something(self):
        """(N pts) Description."""
        fn = load()
        assert fn(...) == expected
```

## Adding Providers

Edit `providers.py` — add a `send_<provider>()` function and register it in the `PROVIDERS` dict. The function signature is: `(system: str, user: str, config: dict) -> str`.
