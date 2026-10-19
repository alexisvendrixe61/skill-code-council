---
name: code-council
description: "Multi-agent code council: specialist agents with conflicting lenses (bugs, architecture, simplicity, plus readability and operability in full mode) analyze code independently, their claims are fact-checked against the code, and a chairman delivers a prioritized verdict, then optionally implements it on an isolated git worktree branch. Three modes: REVIEW a repo, folder, diff or PR; SOLVE a feature or task inside an existing repo by comparing competing designs; BUILD a new project from scratch. Use this whenever the user asks to council, deeply review, audit, pressure-test or refactor a codebase, wants several perspectives on how to implement something, asks how to architect or start a new project, or wants a second opinion on a PR, even if they don't say 'council'. Not for one-line fixes, quick syntax questions or explaining a single snippet."
---

# Code Council

One reviewer gives one perspective and confidently invents some of its findings. The council runs the code (or the task) through five agents whose lenses deliberately pull against each other. They then fact-check each other's claims against the real code, and a chairman turns what survives into a prioritized verdict. If the user approves, an implementer executes the verdict on an isolated branch.

Adapted from Karpathy's LLM Council: independent answers → anonymous peer review → chairman synthesis.

## The four rules, and why they exist

1. **The user's branch and working tree are never modified.** The user may have work in progress, and an agent rewriting their branch is the fastest way to lose their trust. All changes go to a git worktree on a `council/<mode>-<timestamp>` branch. Don't checkout, commit to, merge into, rebase, reset or push the original branch, and don't push anything at all unless asked. The user decides whether to merge.
2. **Every finding cites `path:line`.** Uncited findings are where hallucinations hide. Peer review checks the citations, and false positives never reach the report.
3. **Code the council writes follows `references/standards.md`:** easy to understand, small functions. These are the user's priorities, and the same standards are a review lens for existing code.
4. **Phases 0–4 are read-only. Phase 5 starts only after an explicit yes.** A review is cheap to ignore, but unrequested code changes are not.

## Paths: use literal values

Shell variables don't survive between separate commands. The helper scripts print absolute paths (`OUT=…`, `TS=…`, `WT=…`). Copy those literal values into every later command and agent prompt instead of writing `$OUT`.

`SKILL_DIR` below means the directory containing this file.

---

## Pick the mode

| Mode | Use when | Council produces | Act phase produces |
|---|---|---|---|
| **review** | Existing code, a folder, a diff/PR | Verified, prioritized findings (P0–P2) | Fix commits on a council branch |
| **solve** | A task to accomplish inside an existing repo | 5 competing approaches → one chosen design | Implementation on a council branch |
| **build** | A new project from scratch | 5 competing architectures → one design, layout and milestones | Scaffolded project + first working slice |

If the mode is genuinely ambiguous, ask one question.

**Quick or full:**
- **Quick** (the default): 3 advisors (Breaker, Architect, Simplifier), no peer round. You verify P0/P1 findings yourself and write the verdict yourself with the chairman template.
- **Full:** all 5 advisors, 5 peer reviewers, 1 chairman. Run it only when the user asks for it ("full council", "full", "thorough", "deep review", "all five").

The user chose quick as the default: in testing it caught the same critical bugs at about 40% of the cost and half the time. When the scope is large or high-stakes (more than ~50 source files, security-sensitive code, or a build), mention in one line at the end of the Phase 4 summary that a full council is available. Don't switch to full on your own.

---

## Phase 0: Recon (you, no agents)

Goal: a short, factual **brief**, so advisors give grounded answers instead of generic ones. Keep it to a few minutes, since the advisors will read the code themselves.

### review / solve

1. From the repo root, run:
   ```bash
   bash SKILL_DIR/scripts/recon.sh <review|solve> [scope paths…]
   ```
   It does the following:
   - creates `.council/<TS>/` (kept out of git through `.git/info/exclude`, so no tracked file changes)
   - records the base branch and SHA
   - runs the tests, lizard (function size, complexity and parameters) and ruff for Python, each with a timeout
   - writes `signals.md` and `meta.json`

   Note the printed `OUT` and `TS`.
2. **Edge cases:**
   - **Not a git repo:** reviewing still works. Before any act phase, ask whether to `git init` and commit the current state, since worktrees need git.
   - **Uncommitted changes** (`UNCOMMITTED>0`): tell the user. Advisors review the working tree as it is, but the act phase branches from the last commit, so suggest they commit first if the changes matter.
   - **Large repo** (more than ~150 source files in scope): ask the user to narrow the scope, or pick the highest-risk area (the entry points plus the files lizard flags) and say so in the brief.
3. **Read the context:** `README*`, `CLAUDE.md`, the manifest (`pyproject.toml`, `package.json`, `go.mod`…) and any earlier `.council/*/verdict.md`, so the council doesn't repeat past ground.
4. **Set the scope:**
   - whole repo
   - a path
   - a diff (`git diff <base>...HEAD`, or `gh pr diff <n>` for a PR)
   - for solve mode, the task plus the files it will touch
5. **Write `OUT/brief.md`** with:
   - `Goal:` (one line, used as the report title)
   - the mode and the scope (file list)
   - the stack
   - a summary of `signals.md`: test result, lizard and ruff counts, worst offenders
   - constraints from CLAUDE.md
   - the standards summary (last section of `references/standards.md`)

### build

There's no code yet, so recon means requirements. If any of these are unclear, ask, with at most 3 questions in one message:
- what the software does and for whom
- hard constraints: language, deployment target, data, integrations
- what "done" looks like for a first version

If the user already gave enough detail, don't ask; proceed and state your assumptions in the brief.

Then:
1. Run `bash SKILL_DIR/scripts/recon.sh build` from the folder where the project will live.
2. Write `OUT/brief.md`. The default language is Python unless the user says otherwise.

---

## Phase 1: Council (parallel)

Spawn all advisors **in one message**, so they run in parallel and can't influence each other. Use the Agent tool (`subagent_type: general-purpose`).

Build each prompt from the advisor template in `references/prompts.md`, with:
- the advisor's Core paragraph and current-mode paragraph from `references/advisors.md`
- the full brief
- the standards summary

Advisors are read-only. They open files themselves and cite `path:line`.

Save each response verbatim to `OUT/advisor-<name>.md`, using lowercase names: breaker, architect, simplifier, newcomer, operator.

**If the Agent tool isn't available** (for example when you are yourself running as a sub-agent), play each advisor yourself, one at a time. Write each response to its file before starting the next, and fully adopt each lens. This loses some independence, so mention it in the brief.

---

## Phase 2: Peer review and verification (full mode, parallel)

1. Shuffle the mapping:
   ```bash
   python3 SKILL_DIR/scripts/shuffle.py OUT
   ```
   It writes `mapping.md` and prints, for example, `A = newcomer`. Anonymity matters: reviewers who know which lens wrote what defer to the lens instead of judging the evidence.
2. Spawn 5 reviewers in one message with the reviewer template.
3. Each reviewer picks the strongest response and the biggest blind spot, names what everyone missed, and **verifies findings against the code**. Every P0/P1 finding (or every key claim of a proposal) gets marked `CONFIRMED`, `DISPUTED` or `FALSE POSITIVE` with a reason. This verification is the main thing separating the council from "ask five times".
4. Save the reviews to `OUT/review-1.md` through `review-5.md`.

**Quick mode:** skip this phase. Open each cited P0/P1 location yourself and mark it the same way in `OUT/review-1.md`.

---

## Phase 3: Chairman

Spawn one agent with the chairman template for the current mode (review, or solve/build). Give it:
- the brief
- the de-anonymized advisor responses
- the reviews, with the mapping

The chairman:
- merges duplicate findings
- drops false positives
- keeps disputed items only with a note
- may side with a minority advisor whose evidence is stronger

Save the result to `OUT/verdict.md`.

**Quick mode:** write the verdict yourself with the same chairman template, so the report and its headings stay identical.

Keep the section headings exactly as the template gives them, because the report renderer finds sections by their headings. The same goes for the `Advisor | stance | concern` lines under "Advisor alignment".

---

## Phase 4: Report

1. Run:
   ```bash
   python3 SKILL_DIR/scripts/render_report.py OUT
   ```
   It builds `OUT/report.html` from the brief, verdict, advisors, reviews and mapping. Don't hand-write the HTML.
2. Write `OUT/transcript.md`, concatenating:
   - the brief
   - all advisor responses
   - the mapping and all reviews
   - the verdict
3. Try to open the report: `open` on macOS, `xdg-open` on Linux. If neither works, give the absolute path.
4. In chat, keep it short:
   - the verdict in 2–3 sentences
   - the top 3 items
   - the one thing to do first
   - the report path
   - **then ask:** "Want me to implement this on a council branch? Your current branch stays untouched."

If the user's original request already explicitly asked for implementation ("review and fix it", "build it"), that counts as the yes. Continue to Phase 5 without asking again.

---

## Phase 5: Act (only after a yes)

### Worktree

- **review / solve:** from the repo, run:
  ```bash
  bash SKILL_DIR/scripts/make_worktree.sh <mode> <TS> <base-sha>
  ```
- **build:** run:
  ```bash
  bash SKILL_DIR/scripts/make_worktree.sh build <TS> <new-project-dir>
  ```
  This creates the repo with an empty `main` commit, so the scaffold lands on a council branch exactly like the other modes.

The script prints `WT`, `BRANCH` and `BASE`. Before every git write, run `bash SKILL_DIR/scripts/guard.sh <WT>`. It exits non-zero unless the worktree is on a `council/` branch, which is the mechanical backstop for rule 1.

### Implement

Spawn one implementer agent with the implementer template. Give it:
- the literal `WT`, `BRANCH` and guard script path
- the verdict
- the full `standards.md`

The implementer:
- touches files only under `WT`
- makes one small commit per item, referencing its finding or step ID
- runs the tests after each commit, and reverts its own commit if it breaks them
- finishes with lizard on the changed files

### Check the result yourself

The implementer is graded by you, not by itself:
1. Read `git -C <WT> diff <BASE>..HEAD` against the standards.
2. Re-run the tests and `lizard -w -L 30 -C 10 -a 4` on the changed files.
3. Fix or flag anything off.
4. Confirm the original branch is still at its recorded SHA.

### Hand back

1. Write `OUT/act.md` with:
   - the branch and worktree path
   - one line per commit
   - tests before → after
   - skipped items and why
2. Re-run `render_report.py` so the report includes the act results.
3. Give the user these commands without running them:
   ```bash
   git diff <original-branch>...<BRANCH>                       # inspect
   git merge <BRANCH>                                          # adopt (run from their branch)
   git worktree remove <WT> && git branch -D <BRANCH>          # discard
   ```

---

## Files in this skill

| File | Read it when |
|---|---|
| `references/advisors.md` | Phase 1: the five lenses, with a paragraph per mode |
| `references/prompts.md` | Phases 1–3 and 5: advisor, reviewer, chairman and implementer templates |
| `references/standards.md` | Phase 0 (the summary goes into every prompt) and Phase 5 (in full, for the implementer) |
| `scripts/recon.sh` | Phase 0: output folder, base SHA, tests, lizard, ruff |
| `scripts/shuffle.py` | Phase 2: anonymization mapping |
| `scripts/render_report.py` | Phase 4: HTML report (uses `assets/report.css`) |
| `scripts/make_worktree.sh`, `scripts/guard.sh` | Phase 5: isolated branch and the branch safety check |
