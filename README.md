# AI Code Generation Eval - Python

A practical benchmark for measuring how well an AI model generates production-quality code.

This is derived out of my blog post regarding Vibe Coding and making it more AI readable.

[Vibe Coding - Prompts are all you need](../vibe-coding-prompts-are-all-you-need.md)

*Published on [Towards AI](https://pub.towardsai.net/vibe-coding-prompts-are-all-you-need-1902215294bb) · October 31, 2025*

## Why This Exists

Most public benchmarks test whether code *runs*. HumanEval, MBPP, LiveCodeBench — they give a function spec and check if the output is correct. SWE-bench tests bug-fixing on real GitHub issues. None of them test:

- Will the model use `float` for money calculations?
- Will it inject SQL via the ORDER BY clause?
- Will its rate limiter overdraft under concurrency?
- Will it add `if/elif` branches instead of following the Open-Closed Principle?
- Will its tests only cover the happy path and miss a planted bug?

These are the failure modes that actually bite you in production. A model that scores 90 on HumanEval can still write a float-based ledger, a racy rate limiter, and tests that all pass on buggy code. This eval catches that.

**The c10 meta-challenge** — testing whether a model can write tests that catch a real planted bug — evaluates the model as a TDD partner, not just a code generator. No major eval does this.

### What it's good for

- **Choosing a model for a specific project** — "I need strong security and concurrency, which model?" This answers that better than HumanEval.
- **Catching model regressions** — When a model version updates, run it and diff against the timestamped previous run.
- **Making the case internally** — "We should use Sonnet, not Haiku, for our payment service" — the money arithmetic challenge gives you concrete evidence.

### Known limitations

- **11 challenges is too small for statistical confidence.** One lucky or unlucky challenge can swing the score 10-15 points. You'd need 30-50 per category before rankings are reliable.
- **You're testing model + system prompt, not model alone.** The system prompt in `eval_config.yaml` meaningfully affects results. Different prompts can shift scores 10-20%.
- **Not a replacement for official benchmarks** — for raw capability comparisons, SWE-bench Verified or LiveCodeBench are better. This fills a different niche: production code quality.

---

## Philosophy

This eval tests whether code is **correct at the edges, secure by default, well-designed, and maintainable** — the things that separate a demo from production.

Each challenge targets a specific failure mode that real AI models exhibit. The challenges are calibrated so that:
- State-of-the-art models (Opus-class) score **90-100**
- Strong models (Sonnet-class) score **75-85**
- Mid-tier models score **55-70**
- Weak models score **below 50**

The score tells you: *"Can I trust this model for this category of work?"*

## Quick Start

## Manual Mode - If you have Web/GUI/Terminal Subscription Access

```bash
cd eval/python
pip install pyyaml anthropic openai    # install what you need
```

```
python run_eval.py --list                    # Lists all Prompt Ids
```

```
python3 run_eval.py --list

  ID                           Category                   Diff   Pts
  ──────────────────────────────────────────────────────────────────
  c01_off_by_one               Algorithmic Correctness       *     8
  c02_floating_point           Algorithmic Correctness      **    12
  c03_edge_cases               Edge Cases & Boundaries      **    10
  c04_security                 Security                     **    15
  c05_concurrency              Concurrency                 ***    10
  c06_error_handling           Error Handling               **    10
  c07_design_solid             Design & SOLID               **    20
  c08_refactoring              Refactoring                  **    10
  c09_edge_boundaries          Edge Cases & Boundaries      **     5
  c10_test_generation          Algorithmic Correctness     ***    10
  c11_algorithmic_hard         Algorithmic Correctness     ***    15
  ──────────────────────────────────────────────────────────────────
  11 challenges                                           125 pts

```

# Interactive mode: show prompt, paste solution, auto-score
python run_eval.py --prompt c01_off_by_one      # One challenge: show prompt, paste, score
python run_eval.py --prompts                    # All challenges in a loop (ESC )

# Workflow:
- 1. The prompt is printed to the terminal
- 2. Paste the model's response, then press Ctrl+D to submit
- 3. Solution is saved to solutions/manual/<timestamp>/<challenge>.py
- 4. Auto-scored immediately; result printed inline
- 5. For --prompts: press Enter to continue to next challenge, ESC to exit
- 6. Re-score the whole session: python run_eval.py --score -c manual/<timestamp>

python run_eval.py --score                      # Score solutions/ directory
python run_eval.py --score -c c01_off_by_one    # Score one challenge
```

# Auto Mode - If you have API keys and billing set

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
