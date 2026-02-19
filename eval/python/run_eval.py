#!/usr/bin/env python3
"""
AI Code Generation Eval Runner

Usage:
    # Manual mode: paste model outputs into solutions/ then score
    python run_eval.py --score

    # Auto mode: send prompts to models via API, save solutions, score
    python run_eval.py --auto                                    # All models in config
    python run_eval.py --auto --model claude-opus                # One model
    python run_eval.py --auto --model gpt-4o --challenge c01_off_by_one

    # Show all challenge prompts (for manual copy-paste)
    python run_eval.py --prompts

    # Compare results across models
    python run_eval.py --compare
"""

import argparse
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import re
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime


EVAL_DIR = Path(__file__).parent
CHALLENGES_DIR = EVAL_DIR / "challenges"
SOLUTIONS_DIR = EVAL_DIR / "solutions"
RESULTS_DIR = EVAL_DIR / "results"
CONFIG_FILE = EVAL_DIR / "eval_config.yaml"

CATEGORIES = {
    "algorithmic_correctness": "Algorithmic Correctness",
    "edge_cases": "Edge Cases & Boundaries",
    "security": "Security",
    "concurrency": "Concurrency",
    "error_handling": "Error Handling",
    "design_solid": "Design & SOLID",
    "refactoring": "Refactoring",
}


@dataclass
class ChallengeInfo:
    name: str
    category: str
    difficulty: int
    points: int
    why: str
    prompt: str
    file_path: Path


@dataclass
class ChallengeResult:
    name: str
    category: str
    points_earned: float
    points_total: int
    passed: int
    failed: int
    errors: int
    details: str


# ---------------------------------------------------------------------------
# Challenge discovery & parsing
# ---------------------------------------------------------------------------

def parse_challenge(file_path: Path) -> ChallengeInfo:
    """Parse challenge metadata and prompt from a challenge file."""
    source = file_path.read_text()

    category = ""
    difficulty = 1
    points = 0
    why = ""
    for line in source.split("\n"):
        stripped = line.strip()
        if stripped.startswith("CATEGORY:"):
            category = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("DIFFICULTY:"):
            difficulty = int(stripped.split(":", 1)[1].strip())
        elif stripped.startswith("POINTS:"):
            points = int(stripped.split(":", 1)[1].strip())
        elif stripped.startswith("WHY:"):
            why = stripped.split(":", 1)[1].strip()

    spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    prompt = getattr(mod, "PROMPT", "").strip()

    return ChallengeInfo(
        name=file_path.stem, category=category, difficulty=difficulty,
        points=points, why=why, prompt=prompt, file_path=file_path,
    )


def discover_challenges() -> list[ChallengeInfo]:
    challenges = []
    for f in sorted(CHALLENGES_DIR.glob("c*.py")):
        if f.name == "__init__.py":
            continue
        try:
            challenges.append(parse_challenge(f))
        except Exception as e:
            print(f"  Warning: failed to parse {f.name}: {e}")
    return challenges


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_challenge_tests(challenge: ChallengeInfo, solutions_dir: Path = None) -> ChallengeResult:
    """Run pytest for a single challenge against a solutions directory."""
    sol_dir = solutions_dir or SOLUTIONS_DIR
    solution_file = sol_dir / f"{challenge.name}.py"

    if not solution_file.exists():
        return ChallengeResult(
            name=challenge.name, category=challenge.category,
            points_earned=0, points_total=challenge.points,
            passed=0, failed=0, errors=0, details="NO SOLUTION FILE",
        )

    # Set PYTHONPATH so challenge imports resolve to the right solutions dir
    env = os.environ.copy()
    env["PYTHONPATH"] = str(sol_dir.parent)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(challenge.file_path), "-v", "--tb=short", "-q"],
        capture_output=True, text=True, cwd=str(EVAL_DIR), env=env, timeout=120,
    )

    output = result.stdout + result.stderr
    passed = failed = errors = 0
    for line in output.split("\n"):
        m = re.search(r"(\d+) passed", line)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+) failed", line)
        if m:
            failed = int(m.group(1))
        m = re.search(r"(\d+) error", line)
        if m:
            errors = int(m.group(1))

    total = passed + failed + errors
    if total == 0:
        points_earned = 0.0
        details = "NO TESTS RAN"
    else:
        points_earned = round(challenge.points * (passed / total), 1)
        details = f"{passed}/{total} tests passed"

    failure_lines = [l.strip() for l in output.split("\n") if "FAILED" in l]
    if failure_lines:
        details += "\n    Failures:\n" + "".join(f"      - {fl}\n" for fl in failure_lines)

    return ChallengeResult(
        name=challenge.name, category=challenge.category,
        points_earned=points_earned, points_total=challenge.points,
        passed=passed, failed=failed, errors=errors, details=details,
    )


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load eval_config.yaml."""
    try:
        import yaml
    except ImportError:
        print("Error: PyYAML required for config. Install with: pip install pyyaml")
        sys.exit(1)

    if not CONFIG_FILE.exists():
        print(f"Error: {CONFIG_FILE} not found")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Auto mode: send prompts to models via API
# ---------------------------------------------------------------------------

def run_auto(challenges: list[ChallengeInfo], model_name: str, model_config: dict,
             system_prompt: str, specific_challenge: str = None):
    """Send challenge prompts to a model, save solutions, score them."""
    from providers import send_prompt, extract_code

    # Create per-model solutions and results directories
    model_solutions = RESULTS_DIR / model_name / "solutions"
    model_solutions.mkdir(parents=True, exist_ok=True)
    (model_solutions / "__init__.py").touch()

    print(f"\n  Model: {model_name} ({model_config['provider']}/{model_config['model']})")
    print(f"  {'─'*55}")

    results = []
    for c in challenges:
        if specific_challenge and c.name != specific_challenge:
            continue

        solution_file = model_solutions / f"{c.name}.py"

        # Check if solution already exists (skip re-generation)
        if solution_file.exists() and solution_file.stat().st_size > 0:
            print(f"  {c.name}: cached", end="", flush=True)
        else:
            print(f"  {c.name}: querying {model_config['model']}...", end="", flush=True)
            try:
                start = time.time()
                raw_response = send_prompt(system_prompt, c.prompt, model_config)
                elapsed = time.time() - start
                code = extract_code(raw_response)
                solution_file.write_text(code)

                # Also save raw response for debugging
                raw_file = model_solutions / f"{c.name}.raw.txt"
                raw_file.write_text(raw_response)

                print(f" ({elapsed:.1f}s)", end="", flush=True)
            except Exception as e:
                print(f" ERROR: {e}")
                results.append(ChallengeResult(
                    name=c.name, category=c.category,
                    points_earned=0, points_total=c.points,
                    passed=0, failed=0, errors=1, details=f"API ERROR: {e}",
                ))
                continue

        # Score it
        r = run_challenge_tests(c, solutions_dir=model_solutions)
        results.append(r)
        status = "PASS" if r.points_earned == r.points_total else "PARTIAL"
        print(f" -> [{status}] {r.points_earned}/{r.points_total}")

    # Save results JSON
    results_file = RESULTS_DIR / model_name / "results.json"
    results_data = {
        "model_name": model_name,
        "provider": model_config["provider"],
        "model_id": model_config["model"],
        "timestamp": datetime.now().isoformat(),
        "results": [asdict(r) for r in results],
    }
    with open(results_file, "w") as f:
        json.dump(results_data, f, indent=2)

    # Display scorecard
    display_scorecard(results, title=f"Python — {model_name}")

    return results


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def display_scorecard(results: list[ChallengeResult], title: str = "Python"):
    """Display formatted scorecard."""
    if not results:
        print("  No results to display.")
        return

    # Only count challenges that were actually attempted (have a solution file)
    attempted = [r for r in results if r.details != "NO SOLUTION FILE"]
    skipped = [r for r in results if r.details == "NO SOLUTION FILE"]

    cat_scores: dict[str, dict] = {}
    for r in attempted:
        if r.category not in cat_scores:
            cat_scores[r.category] = {"earned": 0, "total": 0}
        cat_scores[r.category]["earned"] += r.points_earned
        cat_scores[r.category]["total"] += r.points_total

    total_earned = sum(r.points_earned for r in attempted)
    total_possible = sum(r.points_total for r in attempted)

    print()
    print("=" * 60)
    print(f"  AI CODE GENERATION EVAL — {title}")
    print("=" * 60)
    print()
    print(f"  {'Category':<30} {'Score':>8}  {'Pct':>5}")
    print(f"  {'─'*48}")

    for cat_key, cat_name in CATEGORIES.items():
        if cat_key in cat_scores:
            s = cat_scores[cat_key]
            pct = round(100 * s["earned"] / s["total"]) if s["total"] > 0 else 0
            print(f"  {cat_name:<30} {s['earned']:>4}/{s['total']:<4} {pct:>4}%")

    print(f"  {'─'*48}")
    pct_total = round(100 * total_earned / total_possible) if total_possible > 0 else 0
    print(f"  {'TOTAL':<30} {total_earned:>4}/{total_possible:<4} {pct_total:>4}%")
    if skipped:
        skipped_pts = sum(r.points_total for r in skipped)
        print(f"  ({len(skipped)} challenges skipped — {skipped_pts} pts not attempted)")
    print()

    weaknesses = [r for r in attempted if r.points_earned < r.points_total]
    if weaknesses:
        print("  Weaknesses:")
        for w in weaknesses:
            print(f"    - {CATEGORIES.get(w.category, w.category)}: {w.name} "
                  f"({w.details.split(chr(10))[0]})")
        print()

    if pct_total >= 90:
        tier = "Opus-class (state of the art)"
    elif pct_total >= 75:
        tier = "Sonnet-class (strong)"
    elif pct_total >= 55:
        tier = "Mid-tier"
    else:
        tier = "Below mid-tier — review AI output carefully"
    print(f"  Model tier: {tier}")
    print()


def show_prompts(challenges: list[ChallengeInfo], specific: str = None):
    for c in challenges:
        if specific and c.name != specific:
            continue
        print(f"\n{'='*70}")
        print(f"  CHALLENGE: {c.name}")
        print(f"  Category:  {CATEGORIES.get(c.category, c.category)}")
        print(f"  Points:    {c.points}  |  Difficulty: {'*' * c.difficulty}")
        print(f"{'='*70}\n")
        print(c.prompt)
        print(f"\n  Save to: solutions/{c.name}.py")
        print(f"{'='*70}")


def run_compare():
    """Compare results across all evaluated models."""
    if not RESULTS_DIR.exists():
        print("No results yet. Run --auto first.")
        return

    all_results = {}
    for model_dir in sorted(RESULTS_DIR.iterdir()):
        results_file = model_dir / "results.json"
        if results_file.exists():
            with open(results_file) as f:
                data = json.load(f)
                all_results[data["model_name"]] = data

    if not all_results:
        print("No results found.")
        return

    # Collect all challenge names
    all_challenges = set()
    for data in all_results.values():
        for r in data["results"]:
            all_challenges.add(r["name"])
    all_challenges = sorted(all_challenges)

    # Header
    models = list(all_results.keys())
    col_w = max(12, max(len(m) for m in models) + 2)

    print()
    print("=" * (30 + col_w * len(models)))
    print("  MODEL COMPARISON")
    print("=" * (30 + col_w * len(models)))
    print()
    print(f"  {'Challenge':<28}", end="")
    for m in models:
        print(f"{m:>{col_w}}", end="")
    print()
    print(f"  {'─' * (26 + col_w * len(models))}")

    # Per-challenge scores
    model_totals = {m: {"earned": 0, "total": 0} for m in models}
    for ch_name in all_challenges:
        print(f"  {ch_name:<28}", end="")
        for m in models:
            data = all_results[m]
            r = next((r for r in data["results"] if r["name"] == ch_name), None)
            if r:
                score_str = f"{r['points_earned']}/{r['points_total']}"
                model_totals[m]["earned"] += r["points_earned"]
                model_totals[m]["total"] += r["points_total"]
            else:
                score_str = "—"
            print(f"{score_str:>{col_w}}", end="")
        print()

    # Totals
    print(f"  {'─' * (26 + col_w * len(models))}")
    print(f"  {'TOTAL':<28}", end="")
    for m in models:
        t = model_totals[m]
        pct = round(100 * t["earned"] / t["total"]) if t["total"] > 0 else 0
        print(f"{t['earned']}/{t['total']} ({pct}%):>{col_w}".replace(":>", ""), end="  ")
    print()

    # Category breakdown
    print()
    print(f"  {'BY CATEGORY':<28}", end="")
    for m in models:
        print(f"{m:>{col_w}}", end="")
    print()
    print(f"  {'─' * (26 + col_w * len(models))}")

    for cat_key, cat_name in CATEGORIES.items():
        print(f"  {cat_name:<28}", end="")
        for m in models:
            data = all_results[m]
            earned = sum(r["points_earned"] for r in data["results"] if r["category"] == cat_key)
            total = sum(r["points_total"] for r in data["results"] if r["category"] == cat_key)
            if total > 0:
                pct = round(100 * earned / total)
                print(f"{pct:>{col_w-1}}%", end="")
            else:
                print(f"{'—':>{col_w}}", end="")
        print()
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AI Code Generation Eval",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_eval.py --prompts                              # Show prompts for manual use
  python run_eval.py --score                                # Score solutions/ directory
  python run_eval.py --score -c gemini3_fast                # Score all in solutions/gemini3_fast/
  python run_eval.py --score -c gemini3_fast/c01_off_by_one # Score one challenge for one model
  python run_eval.py --auto                                 # Run all models from config
  python run_eval.py --auto --model claude-opus             # Run one model
  python run_eval.py --auto --model gpt-4o -c c01_off_by_one  # One model, one challenge
  python run_eval.py --compare                              # Side-by-side comparison
  python run_eval.py --auto --rerun                         # Re-run (ignore cached solutions)
        """,
    )
    parser.add_argument("--prompts", action="store_true", help="Show all challenge prompts")
    parser.add_argument("--prompt", type=str, help="Show one challenge prompt")
    parser.add_argument("--score", action="store_true", help="Score solutions/ directory (manual mode)")
    parser.add_argument("--auto", action="store_true", help="Auto mode: query models via API")
    parser.add_argument("--model", "-m", type=str, help="Specific model name from eval_config.yaml")
    parser.add_argument("--challenge", "-c", type=str, help="Specific challenge name")
    parser.add_argument("--compare", action="store_true", help="Compare all evaluated models")
    parser.add_argument("--rerun", action="store_true", help="Re-generate solutions (ignore cache)")
    args = parser.parse_args()

    challenges = discover_challenges()
    if not challenges:
        print("No challenges found in challenges/")
        sys.exit(1)

    if args.prompts or args.prompt:
        show_prompts(challenges, specific=args.prompt)

    elif args.score:
        # Resolve model folder and challenge filter from -c argument.
        # Supports:  -c c01_off_by_one              (solutions/)
        #            -c gemini3_fast/c01_off_by_one  (solutions/gemini3_fast/)
        #            -c gemini3_fast                 (all challenges in that folder)
        sol_dir = SOLUTIONS_DIR
        challenge_filter = args.challenge
        model_label = None

        if challenge_filter:
            if "/" in challenge_filter:
                parts = challenge_filter.split("/", 1)
                model_label = parts[0]
                challenge_filter = parts[1] if parts[1] else None
                sol_dir = SOLUTIONS_DIR / model_label
            else:
                # Could be a model folder name (no matching challenge) or a challenge name
                candidate_dir = SOLUTIONS_DIR / challenge_filter
                if candidate_dir.is_dir():
                    model_label = challenge_filter
                    sol_dir = candidate_dir
                    challenge_filter = None

            if not sol_dir.exists():
                print(f"Error: solutions directory not found: {sol_dir}")
                print(f"Available: {', '.join(d.name for d in SOLUTIONS_DIR.iterdir() if d.is_dir() and d.name != '__pycache__')}")
                sys.exit(1)

        title = f"Python — {model_label}" if model_label else "Python"
        results = []
        for c in challenges:
            if challenge_filter and c.name != challenge_filter:
                continue
            print(f"  Scoring {c.name}...", end=" ", flush=True)
            r = run_challenge_tests(c, solutions_dir=sol_dir)
            results.append(r)
            status = "PASS" if r.points_earned == r.points_total else (
                "SKIP" if r.details == "NO SOLUTION FILE" else "PARTIAL"
            )
            print(f"[{status}] {r.points_earned}/{r.points_total}")
        display_scorecard(results, title=title)

    elif args.auto:
        config = load_config()
        system_prompt = config.get("system_prompt", "Write Python code. Return only code.")
        models_config = config.get("models", {})

        if args.model:
            # Run a specific model
            if args.model not in models_config:
                print(f"Error: model '{args.model}' not found in eval_config.yaml")
                print(f"Available: {', '.join(models_config.keys())}")
                sys.exit(1)
            model_cfg = models_config[args.model]

            if args.rerun:
                # Delete cached solutions
                model_sol = RESULTS_DIR / args.model / "solutions"
                if model_sol.exists():
                    for f in model_sol.glob("*.py"):
                        if f.name != "__init__.py":
                            f.unlink()
                    for f in model_sol.glob("*.raw.txt"):
                        f.unlink()

            run_auto(challenges, args.model, model_cfg, system_prompt, args.challenge)
        else:
            # Run all models
            for model_name, model_cfg in models_config.items():
                try:
                    run_auto(challenges, model_name, model_cfg, system_prompt, args.challenge)
                except Exception as e:
                    print(f"\n  {model_name}: SKIPPED ({e})")

            # Auto-compare if multiple models ran
            if len(models_config) > 1:
                run_compare()

    elif args.compare:
        run_compare()

    else:
        print("AI Code Generation Eval")
        print(f"  {len(challenges)} challenges | {sum(c.points for c in challenges)} total points")
        print()
        print("Modes:")
        print("  --prompts                  Show challenge prompts (for manual copy-paste)")
        print("  --score                    Score solutions/ directory (manual mode)")
        print("  --auto                     Query models via API and score automatically")
        print("  --auto --model MODEL       Query a single model")
        print("  --compare                  Compare results across models")
        print()
        print("Quick start:")
        print("  1. Set API keys: export ANTHROPIC_API_KEY=sk-...")
        print("  2. Run: python run_eval.py --auto --model claude-sonnet")


if __name__ == "__main__":
    main()
