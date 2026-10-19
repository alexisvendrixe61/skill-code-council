# code-council

A Claude Code skill: a multi-agent code council that reviews code, solves tasks in an existing repo, or builds a new project from scratch.

- **Quick mode by default:** 3 advisors (Breaker, Architect, Simplifier), findings verified against the code. Say "full council" for all 5 advisors plus anonymous peer review.
- **Safe by design:** changes only ever land on a `council/*` branch in a separate git worktree. Your branch is never touched.
- **Standards:** easy-to-understand code, small functions (≤30 lines, complexity ≤10, ≤4 parameters), checked with lizard.

## Install

```bash
git clone git@github.com:<you>/code-council.git ~/.claude/skills/code-council
```

In Claude Code, run `/skills` to check it's listed.

## Use

```
quick council review this repo
council review src/api and fix the P0 issues
council: how should I add CSV export? design only
council a new project: <what it does, for whom, v1 scope>. Build the first version in ./myproject
```

## Update

```bash
git -C ~/.claude/skills/code-council pull
```

## Layout

| Path | Purpose |
|---|---|
| `SKILL.md` | The skill instructions Claude reads |
| `references/` | Advisor lenses, prompt templates, code standards |
| `scripts/` | Recon, mapping shuffle, report renderer, worktree and branch guard |
| `assets/report.css` | Report styling |
| `evals/evals.json` | Test prompts for re-testing after changes |
