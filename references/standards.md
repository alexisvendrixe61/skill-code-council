# Code Standards

These standards are the user's priorities. Advisors apply them as a review lens, and the implementer must obey them for every line it writes.

## The two principles

1. **Easy to understand.** A competent developer new to the repo should understand any function in under a minute.
2. **Small functions.** Each function does one thing, and its name says what that thing is.

## Hard limits (checked with `lizard`)

| Metric | Limit | Why |
|---|---|---|
| Function length | **≤ 30 lines** (aim for under 20) | Fits on a screen, so it can be read in one pass |
| Cyclomatic complexity | **≤ 10** (aim for under 6) | Few enough paths to reason about and test |
| Parameters | **≤ 4** | More parameters usually means the function does too much. Group them into a dataclass or config object |
| Nesting depth | **≤ 3** | Use early returns and guard clauses instead of nested if/else. lizard doesn't check this by default, so reviewers check it by eye |

Run the check:
```bash
lizard -l python -w -L 30 -C 10 -a 4 <paths>
```
No output means everything passes. Use `-l javascript`, `-l typescript`, `-l go`, `-l java` and so on for other languages.

Existing code over the limits is a **review finding**. New or changed code over the limits is a **bug in the council's own work**.

## Readability rules

**Names**
- Functions are verbs that say what they return or do: `load_invoices`, `is_expired`, `send_reminder`.
- Variables are nouns that say what they hold: `unpaid_invoices`, not `data`, `tmp` or `res`.
- Booleans read as questions: `is_valid`, `has_access`.
- Avoid unexplained abbreviations. `usr_cfg_mgr` should be `user_settings`.

**Structure**
- Use guard clauses and early returns first, then the main path.
- Name magic numbers and strings as constants: `MAX_RETRIES = 3`.
- Keep one level of abstraction per function. Either orchestrate (call other functions) or do detail work, not both.
- Keep pure logic separate from I/O so the logic is easy to test.
- Prefer plain functions and data over class hierarchies. Add a class when there is state to protect.
- Avoid clever one-liners when two clear lines would do.

**Comments and docs**
- Comments explain *why*, never *what*. If code needs a "what" comment, rename or split it.
- Every public function gets a one-line docstring.
- Every project gets a README with what it is, how to run it, how to test it, and the layout.

**Errors**
- Never write a bare `except:` or swallow exceptions silently.
- Raise specific exceptions with messages that say what went wrong and with which value.
- Validate input at the boundary (CLI, API, file read), then trust it inside.

## Python specifics (default stack)

- Python 3.11+, with type hints on all function signatures.
- Use `pathlib` for paths, `dataclasses` for plain records, f-strings for formatting.
- Tooling: `ruff` (lint and format), `pytest`, `lizard`. Configure it all in `pyproject.toml`.
- New project layout:
  ```
  project/
    pyproject.toml
    README.md
    src/<package>/
      __init__.py
      main.py        # entry point: thin, wires the parts together
      <domain>.py    # pure logic
      <io>.py        # files, network, db
    tests/
      test_<domain>.py
  ```
- Minimal `pyproject.toml` tool config:
  ```toml
  [tool.ruff]
  line-length = 100
  [tool.ruff.lint]
  select = ["E", "F", "I", "B", "UP", "SIM", "C90"]
  [tool.ruff.lint.mccabe]
  max-complexity = 10
  ```

## Other languages

| Language | Lint / format | Tests | Complexity |
|---|---|---|---|
| JavaScript / TypeScript | eslint + prettier (or biome) | vitest / jest | `lizard -l javascript` or `-l typescript` |
| Go | gofmt + go vet + staticcheck | go test | `lizard -l go` or gocyclo |
| Java / Kotlin | checkstyle / detekt | JUnit | `lizard -l java` |
| Rust | rustfmt + clippy | cargo test | clippy `cognitive_complexity` |

Always prefer the repo's own existing tooling and config over these defaults.

## Summary to paste into agent prompts

> Standards: code must be easy to understand and built from small functions. Hard limits are ≤30 lines per function, cyclomatic complexity ≤10, ≤4 parameters and nesting ≤3. Use clear verb names for functions and noun names for variables, guard clauses over nesting, and named constants instead of magic values. Keep pure logic separate from I/O. Comments explain why, not what. Never swallow exceptions. Python: type hints, ruff, pytest.
