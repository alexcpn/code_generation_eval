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
import dotenv

dotenv.load_dotenv()

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

    # Challenges import from "solutions.<name>". When solutions live in a
    # model subfolder (e.g. solutions/gemini3_fast/), we temporarily copy
    # the solution file into the main solutions/ dir, run the test, then
    # remove it. This avoids all pytest sys.path and rootdir complications.
    import shutil
    temp_copy = None

    if sol_dir != SOLUTIONS_DIR:
        temp_copy = SOLUTIONS_DIR / f"{challenge.name}.py"
        # Back up if a file already exists there (shouldn't normally happen)
        backup = None
        if temp_copy.exists():
            backup = temp_copy.with_suffix(".py.bak")
            shutil.copy2(temp_copy, backup)
        shutil.copy2(solution_file, temp_copy)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(challenge.file_path),
             "-v", "--tb=short", "-q"],
            capture_output=True, text=True, cwd=str(EVAL_DIR), timeout=120,
        )
    finally:
        if temp_copy and temp_copy.exists():
            temp_copy.unlink()
            if backup and backup.exists():
                shutil.move(str(backup), str(temp_copy))

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
    """Send challenge prompts to a model, save solutions, score them.

    Solutions are saved under:  solutions/<model_name>/<timestamp>/
    e.g. solutions/gpt-4o/2026-02-19_114523/
    """
    from providers import send_prompt, extract_code

    # Create timestamped run directory under solutions/<model>/
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir = SOLUTIONS_DIR / model_name / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "__init__.py").touch()

    run_label = f"{model_name}/{timestamp}"
    print(f"\n  Model: {model_name} ({model_config['provider']}/{model_config['model']})")
    print(f"  Output: solutions/{run_label}/")
    print(f"  {'─'*55}")

    results = []
    for c in challenges:
        if specific_challenge and c.name != specific_challenge:
            continue

        solution_file = run_dir / f"{c.name}.py"

        print(f"  {c.name}: querying {model_config['model']}...", end="", flush=True)
        try:
            start = time.time()
            raw_response = send_prompt(system_prompt, c.prompt, model_config)
            elapsed = time.time() - start
            code = extract_code(raw_response)
            solution_file.write_text(code)

            # Also save raw response for debugging
            raw_file = run_dir / f"{c.name}.raw.txt"
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
        r = run_challenge_tests(c, solutions_dir=run_dir)
        results.append(r)
        status = "PASS" if r.points_earned == r.points_total else "PARTIAL"
        print(f" -> [{status}] {r.points_earned}/{r.points_total}")

    # Save results JSON alongside solutions
    results_file = run_dir / "results.json"
    results_data = {
        "model_name": model_name,
        "provider": model_config["provider"],
        "model_id": model_config["model"],
        "timestamp": timestamp,
        "run_dir": str(run_dir),
        "results": [asdict(r) for r in results],
    }
    with open(results_file, "w") as f:
        json.dump(results_data, f, indent=2)

    # Display scorecard
    display_scorecard(results, title=f"Python — {run_label}")

    # Print re-score command for convenience
    print(f"  Re-score: python3 run_eval.py --score -c {run_label}")
    print()

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


def show_list(challenges: list[ChallengeInfo]):
    """Print a compact table of all challenge IDs, categories, difficulty, and points."""
    total_pts = sum(c.points for c in challenges)
    print()
    print(f"  {'ID':<28} {'Category':<26} {'Diff':>4}  {'Pts':>4}")
    print(f"  {'─'*66}")
    for c in challenges:
        cat = CATEGORIES.get(c.category, c.category)
        diff = "*" * c.difficulty
        print(f"  {c.name:<28} {cat:<26} {diff:>4}  {c.points:>4}")
    print(f"  {'─'*66}")
    print(f"  {len(challenges)} challenges{'':<41} {total_pts:>4} pts")
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


# ---------------------------------------------------------------------------
# Interactive mode: paste solution, auto-save, auto-score
# ---------------------------------------------------------------------------

def read_multiline_paste() -> str:
    """Read multiline input until Ctrl+D (EOF)."""
    try:
        return sys.stdin.read().strip()
    except KeyboardInterrupt:
        return ""


def wait_for_keypress_continue() -> bool:
    """Wait for a single keypress. Returns True to continue, False on ESC."""
    print("\n  Press Enter to continue, ESC to exit...", end="", flush=True)
    try:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print()
        return ch != "\x1b"
    except (ImportError, Exception):
        # Fallback for environments without termios (Windows, non-tty)
        try:
            user_input = input()
            return user_input.lower() != "q"
        except EOFError:
            return False


def interactive_session(challenges: list[ChallengeInfo], specific: str | None = None):
    """Show challenge prompt(s), read pasted solutions, save and score each.

    Solutions are saved to:  solutions/manual/<timestamp>/<challenge>.py
    All challenges in one --prompts run share the same timestamp folder so
    they can be re-scored together with --score -c manual/<timestamp>.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    session_dir = SOLUTIONS_DIR / "manual" / timestamp
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "__init__.py").touch()

    to_run = [c for c in challenges if specific is None or c.name == specific]
    total = len(to_run)
    all_results = []

    for i, c in enumerate(to_run):
        # Show challenge header and prompt
        print(f"\n{'='*70}")
        print(f"  CHALLENGE: {c.name}  ({i+1}/{total})")
        print(f"  Category:  {CATEGORIES.get(c.category, c.category)}")
        print(f"  Points:    {c.points}  |  Difficulty: {'*' * c.difficulty}")
        print(f"{'='*70}\n")
        print(c.prompt)
        print(f"\n{'─'*70}")
        print("  Paste your solution, then press Ctrl+D:")
        print(f"{'─'*70}\n")

        code = read_multiline_paste()

        if not code.strip():
            print("  (no input — skipping)")
            if i < total - 1:
                if not wait_for_keypress_continue():
                    break
            continue

        # Save solution
        solution_file = session_dir / f"{c.name}.py"
        solution_file.write_text(code)
        print(f"\n  Saved: solutions/manual/{timestamp}/{c.name}.py")

        # Score it
        print(f"  Scoring...", end=" ", flush=True)
        r = run_challenge_tests(c, solutions_dir=session_dir)
        all_results.append(r)
        status = "PASS" if r.points_earned == r.points_total else "PARTIAL"
        print(f"[{status}] {r.points_earned}/{r.points_total}")
        first_line = r.details.split("\n")[0]
        print(f"  {first_line}")

        # Wait between challenges (not after the last one)
        if i < total - 1:
            if not wait_for_keypress_continue():
                print("  Exiting.")
                break

    # Final scorecard for multi-challenge sessions
    if len(all_results) > 1:
        display_scorecard(all_results, title=f"Python — manual/{timestamp}")
        print(f"  Re-score: python3 run_eval.py --score -c manual/{timestamp}")
    elif all_results:
        print(f"\n  Re-score: python3 run_eval.py --score -c manual/{timestamp}")
    elif not to_run:
        print(f"  No challenges matched.")
    print()


def run_compare():
    """Compare results across all evaluated models.

    Finds results.json in:
      solutions/<model>/<timestamp>/results.json   (auto mode)
      results/<model>/results.json                 (legacy)

    For each model, uses the latest timestamped run.
    """
    all_results = {}

    # Scan solutions/<model>/<timestamp>/results.json
    if SOLUTIONS_DIR.exists():
        for model_dir in sorted(SOLUTIONS_DIR.iterdir()):
            if not model_dir.is_dir() or model_dir.name.startswith("__"):
                continue
            # Find latest timestamped subdir with results.json
            run_dirs = sorted(
                [d for d in model_dir.iterdir()
                 if d.is_dir() and (d / "results.json").exists()],
                key=lambda d: d.name,
                reverse=True,
            )
            if run_dirs:
                with open(run_dirs[0] / "results.json") as f:
                    data = json.load(f)
                    label = f"{model_dir.name}/{run_dirs[0].name}"
                    data["_label"] = label
                    all_results[label] = data

    # Also scan legacy results/<model>/results.json
    if RESULTS_DIR.exists():
        for model_dir in sorted(RESULTS_DIR.iterdir()):
            results_file = model_dir / "results.json"
            if results_file.exists():
                with open(results_file) as f:
                    data = json.load(f)
                    label = data["model_name"]
                    if label not in all_results:
                        all_results[label] = data

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
  python run_eval.py --list                                 # List all challenge IDs and points
  python run_eval.py --prompts                              # Show prompts for manual use
  python run_eval.py --score                                # Score solutions/ directory
  python run_eval.py --score -c gemini3_fast                # Score all in solutions/gemini3_fast/
  python run_eval.py --score -c gemini3_fast/c01_off_by_one # Score one challenge for one model
  python run_eval.py --auto                                 # Run all models from config
  python run_eval.py --auto --model claude-opus             # Run one model
  python run_eval.py --auto --model gpt-4o -c c01_off_by_one  # One model, one challenge
  python run_eval.py --compare                              # Side-by-side comparison
  python run_eval.py --score -c gpt-4o/2026-02-19_114523    # Score a timestamped auto run
        """,
    )
    parser.add_argument("--list", action="store_true", help="List all challenge IDs and points")
    parser.add_argument("--prompts", action="store_true", help="Show all challenge prompts")
    parser.add_argument("--prompt", type=str, help="Show one challenge prompt")
    parser.add_argument("--score", action="store_true", help="Score solutions/ directory (manual mode)")
    parser.add_argument("--auto", action="store_true", help="Auto mode: query models via API")
    parser.add_argument("--model", "-m", type=str, help="Specific model name from eval_config.yaml")
    parser.add_argument("--challenge", "-c", type=str, help="Specific challenge name")
    parser.add_argument("--compare", action="store_true", help="Compare all evaluated models")
    parser.add_argument("--re-extract", action="store_true",
                        help="Re-extract .py files from .raw.txt using latest extract_code logic")
    args = parser.parse_args()

    challenges = discover_challenges()
    if not challenges:
        print("No challenges found in challenges/")
        sys.exit(1)

    if args.list:
        show_list(challenges)

    elif args.prompts or args.prompt:
        interactive_session(challenges, specific=args.prompt)

    elif args.score:
        # Resolve model folder and challenge filter from -c argument.
        # Supports:
        #   -c c01_off_by_one                             solutions/c01_off_by_one.py
        #   -c haiku4.5                                   solutions/haiku4.5/  (all challenges)
        #   -c haiku4.5/c01_off_by_one                    solutions/haiku4.5/c01_off_by_one.py
        #   -c gpt-4o/2026-02-19_114523                   solutions/gpt-4o/2026-02-19_114523/ (all)
        #   -c gpt-4o/2026-02-19_114523/c01_off_by_one    solutions/gpt-4o/2026-02-19_114523/c01.py
        sol_dir = SOLUTIONS_DIR
        challenge_filter = args.challenge
        model_label = None

        if challenge_filter:
            # Try the full path as a directory first
            candidate = SOLUTIONS_DIR / challenge_filter
            if candidate.is_dir():
                # It's a folder path (model, model/timestamp, etc.)
                sol_dir = candidate
                model_label = challenge_filter
                challenge_filter = None
            elif "/" in challenge_filter:
                # Split off the last segment as challenge name
                parent_path, ch_name = challenge_filter.rsplit("/", 1)
                parent_dir = SOLUTIONS_DIR / parent_path
                if parent_dir.is_dir():
                    sol_dir = parent_dir
                    model_label = parent_path
                    challenge_filter = ch_name
                else:
                    print(f"Error: directory not found: solutions/{parent_path}")
                    avail = [d.name for d in SOLUTIONS_DIR.iterdir()
                             if d.is_dir() and not d.name.startswith("__")]
                    print(f"Available: {', '.join(sorted(avail))}")
                    sys.exit(1)
            # else: plain challenge name, use default solutions/

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

    elif args.re_extract:
        from providers import extract_code
        # Find all .raw.txt files, re-extract .py from them
        target = args.challenge or ""
        count = 0
        for raw_file in sorted(SOLUTIONS_DIR.rglob("*.raw.txt")):
            if target and target not in str(raw_file):
                continue
            py_file = raw_file.with_suffix("").with_suffix(".py")  # foo.raw.txt -> foo.py
            raw_text = raw_file.read_text()
            new_code = extract_code(raw_text)
            old_code = py_file.read_text() if py_file.exists() else ""
            if new_code != old_code:
                py_file.write_text(new_code)
                rel = raw_file.relative_to(SOLUTIONS_DIR)
                print(f"  Updated: {rel.with_suffix('').with_suffix('.py')}")
                count += 1
        print(f"  {count} file(s) re-extracted." if count else "  All .py files already up to date.")

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
            run_auto(challenges, args.model, models_config[args.model],
                     system_prompt, args.challenge)
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
        print("  --list                     List all challenge IDs and points")
        print("  --prompts                  Show all challenge prompts (for manual copy-paste)")
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
