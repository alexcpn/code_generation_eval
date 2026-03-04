# CLAUDE.md — Universal Template

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
Drop this at the root of any project. Language-specific rules go in subdirectory CLAUDE.md files.

---

## Workflow — How to Work in This Codebase

### Plan Before You Code
- When given a feature or change, **do not write code immediately**.
- First: read the relevant existing code. Understand the current patterns.
- Then: propose a plan — which files to create/modify, what interfaces to define, what tests to write.
- Wait for approval before implementing. Plans are cheap to revise; code is expensive to unwind.

### Work in Small Steps
- Implement one function or one file at a time. Not the whole feature in one shot.
- After each step: run tests, run lint, verify the step works before moving on.
- Commit after each meaningful step — treat commits as save points.

### Contract First, Then Implementation
- Define the interface/type signature and write a doc comment describing behaviour and error conditions.
- Then implement against that contract.
- Then write tests that verify the contract.
- This order matters: it prevents the implementation from defining the API by accident.

### Self-Correction
- When corrected on a pattern, apply the correction to the current task AND note it for future work.
- If you find yourself repeating a mistake, add a rule to this file.

---

## Design Principles — Follow These in All Generated Code

### Single Responsibility
- One file = one concept. One function = one job.
- If a function does two things, split it. If a file has two unrelated types, separate them.
- Handlers parse input and return output. Services contain logic. Repositories do I/O.

### Open-Closed
- New features = new files. Do not modify working code to add functionality.
- Use interfaces so new behaviour is added by implementing, not editing.
- When you must touch existing code, the change should be a single registration or wiring line.

### Dependency Inversion
- Business logic depends on interfaces, never on concrete implementations.
- I/O (database, HTTP, queues) lives behind interfaces injected at startup.
- This makes every layer testable without mocks for unrelated components.

### Explicit Over Implicit
- No global state. No init-time side effects. No magic.
- Configuration is loaded once at startup and passed explicitly.
- Errors are returned, not swallowed. Every error path is handled.

---

## Code Generation Rules

### Before Writing Code
- Read existing code in the same package/directory first. Match the patterns you find.
- Check for existing interfaces that your new code should implement.
- If no clear pattern exists, ask before inventing one.

### While Writing Code
- Every public function/method gets a doc comment stating: what it does, what errors it returns, and any preconditions.
- No hardcoded values — use constants or configuration.
- Wrap errors with context: the caller should know what operation failed and why.
- Add structured logging at: function entry (debug), error paths (error), and key state changes (info).

### After Writing Code
- Generate unit tests covering: happy path, each error condition, edge cases (empty input, nil, zero values, boundary values).
- Run all tests. Do not submit code with failing tests.
- Run the linter. Fix all warnings.

---

## Testing Strategy

### Unit Tests Are Non-Negotiable
- Every new function gets tests. No exceptions for "simple" functions.
- AI-generated code has subtle bugs that only unit tests catch — integration tests are too coarse.
- Tests document intent: a reader should understand the function's behaviour from its tests alone.

### Test Structure
- Cover: happy path, each documented error condition, edge cases (nil, empty, zero, max, duplicates).
- Test names describe the scenario: `TestPortNumber_CoolingPeriodViolation`, not `TestPortNumber3`.
- Tests must not depend on external systems. Use injected mocks/fakes.

### When You Are Unfamiliar With the Code
- Use Claude itself to explain the code before writing tests.
- Ask: "What are the edge cases and failure modes of this function?" then test those.

---

## Code Review Checklist

Use this when reviewing PRs, generated code, or when asked to `/review`:

### Architecture
- [ ] Each file/function has a single, clear responsibility
- [ ] New functionality is in new files — existing working code is not modified unnecessarily
- [ ] Business logic has no direct dependency on I/O (database, HTTP, filesystem)
- [ ] Interfaces are used at layer boundaries (handler -> service -> repo)

### Correctness
- [ ] All error paths are handled — no ignored errors, no bare returns
- [ ] Errors include context (what operation, what input caused it)
- [ ] No data races — shared state is protected or avoided entirely
- [ ] Edge cases considered: nil/null, empty, zero, max values, duplicate calls

### Testability
- [ ] New code has unit tests with meaningful coverage
- [ ] Tests cover happy path AND each documented error condition
- [ ] Tests do not depend on external systems (DB, network, filesystem)
- [ ] Test names describe the scenario, not the implementation

### Security
- [ ] User input is validated before use
- [ ] No SQL string concatenation — parameterised queries only
- [ ] Secrets come from environment/config, never hardcoded
- [ ] API endpoints have authentication and authorisation checks

### Maintainability
- [ ] Public functions have doc comments describing behaviour and errors
- [ ] Structured logging at key points (not print statements)
- [ ] No magic numbers or hardcoded strings — constants or config
- [ ] Code reads top-down without jumping between files to understand one flow

### Observability
- [ ] Errors are logged with enough context to debug without reproducing
- [ ] Key operations have metrics (counters for success/failure, histograms for latency)
- [ ] Request/trace IDs are propagated through the call chain

---

## PR Template

```
## What
One sentence: what this PR does.

## Why
One sentence: why this change is needed.

## How
Bullet list of the key design decisions and files changed.

## Test Plan
How this was tested. Unit tests added, manual verification steps.
```
