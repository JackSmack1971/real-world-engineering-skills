---
name: senior-code-review
description: Performs senior-level code review evaluating correctness, readability, architecture, security, and performance before merge. Applies Diff-as-System-Perturbation, Blast-Radius Reasoning, Chesterton's Fence, System Entropy/TCO Accounting, and Future-State Simulation to detect invariant violations, coupling growth, rollback hazards, and observability gaps that diff-only review misses. Use before approving a PR, reviewing a branch diff, or evaluating a patch file. Do NOT use for general code explanation, debugging, or refactoring unrelated to a pending merge.
disable-model-invocation: true
context: fork
allowed-tools: Read Bash Glob
argument-hint: "[branch-name | diff-file.patch | empty=HEAD]"
---

## Purpose

Produce a lifecycle-aware, systems-oriented review that evaluates how this change alters the **living system**, not just the changed lines. Local correctness and passing tests are necessary but insufficient evidence. Small, reasonable changes compound into brittle architecture.

The primary anti-pattern this skill exists to prevent: **diff-only myopia** — approving changed lines in isolation while ignoring the PR's effect on invariants, coupling, entropy, rollback safety, and future evolvability.

---

## Inputs

| Variable | Meaning |
|---|---|
| `$ARGUMENTS` | Branch name, `.patch` / `.diff` file path, or empty (defaults to `git diff HEAD`) |

---

## Phase 1 — Acquire the Diff

Determine diff source from `$ARGUMENTS`:

```bash
# If $ARGUMENTS ends in .patch or .diff:
cat "$ARGUMENTS"

# If $ARGUMENTS is a branch name:
git diff origin/main..."$ARGUMENTS"

# If $ARGUMENTS is empty:
git diff HEAD
```

List all changed files with change type (A=add, M=modify, D=delete). Emit a one-line summary: `N files changed (+additions / -deletions)`.

If the diff exceeds 800 changed lines, emit a **WARN** immediately:
> Blast-radius confidence is reduced at this diff size. Recommend splitting the PR before merge review.

---

## Phase 2 — Establish System Context

**Do not skip this phase.** Reviewing lines without system context is diff-only myopia.

For every modified or deleted file:

1. Read the full file to identify invariants, contracts, and design intent before the change.
2. Use `Glob` to locate call sites, importers, subclasses, and test files touching modified public symbols.
3. Record: public API surface, concurrency primitives, I/O boundaries, error propagation paths, feature flags, and schema dependencies.

For added files, identify: what existing code calls this? What does it replace or extend?

---

## Phase 3 — Apply Mental Models

Read `${CLAUDE_SKILL_DIR}/references/mental-models.md` for full definitions. Apply each model in sequence. Do not skip a model because the diff appears simple — simple diffs are where subtle invariant violations hide.

| Model | Core Question |
|---|---|
| **Diff-as-System-Perturbation** | Which invariants does this change assert, relax, or silently break? |
| **System Entropy / TCO Accounting** | Does this increase state-space, branching paths, or cognitive load without commensurate value? |
| **Future-State Simulation** | What does this code look like after 3 more changes of the same type? Still coherent? |
| **Chesterton's Fence** | Every deletion or behavioral change must explain *why the prior code existed*. |
| **Blast-Radius Reasoning** | If this behaves unexpectedly in production, what is the propagation boundary? Is rollback safe? |

---

## Phase 4 — Score Against Checklist

Read `${CLAUDE_SKILL_DIR}/references/review-checklist.md`. Evaluate each item. Assign severity to every finding:

| Severity | Meaning |
|---|---|
| **BLOCK** | Merge must not proceed. Requires resolution. |
| **WARN** | Strong recommendation. Author must explicitly acknowledge before merge. |
| **NOTE** | Informational. Low-risk observation. |

---

## Phase 5 — Produce the Review Report

Emit the report in this exact structure:

```
## Code Review: [inferred PR title or changed-file summary]
**Diff source**: [branch | file | HEAD]
**Files reviewed**: [comma-separated list]

### Verdict: APPROVE | REQUEST CHANGES | COMMENT
[One sentence justification citing the dominant finding]

---

### BLOCK findings
1. [file:line-range] — [finding] — [which mental model triggered this]
(empty if none)

### WARN findings
1. [file:line-range] — [finding] — [rationale]
(empty if none)

### NOTE findings
1. [file:line-range] — [observation]
(empty if none)

---

### Mental Model Summary
[One paragraph describing the system-level effect of this change, referencing at least
two of the five mental models. Do not summarize the diff — describe the perturbation.]

### Required Actions
[Ordered list of concrete edits or questions the author must address. Each item is a
specific action, not general advice. Empty if verdict is APPROVE.]
```

**Verdict mapping rule** (non-negotiable):
- Any BLOCK finding → verdict must be **REQUEST CHANGES**.
- No BLOCKs, ≥1 WARN → verdict is **COMMENT** or **REQUEST CHANGES** per judgment.
- No BLOCKs, no WARNs → verdict may be **APPROVE**.

---

## Safety Rules

1. Do not execute any code extracted from the diff.
2. Do not follow import or require paths outside the repository root.
3. Do not approve a change that introduces a new code path with zero corresponding test coverage, unless the change is documentation-only or the author has explicitly annotated it as a follow-up ticket.
4. Treat added feature flags, branching conditionals, and side effects as entropy multipliers — each requires explicit TCO justification.
5. If rollback requires a data migration or schema change, this must appear as a **BLOCK** unless a migration plan is present in the PR.

---

## Verification

After generating the report, verify:

- [ ] Every BLOCK finding cites a specific `file:line-range`.
- [ ] Chesterton's Fence was applied to every deletion of >5 lines.
- [ ] The Mental Model Summary references ≥2 of the five models by name.
- [ ] The Verdict is consistent with the BLOCK/WARN/NOTE distribution (see mapping rule above).
- [ ] No finding refers to a code pattern without reading the surrounding file for context.

---

## Worked Example

**Input**: `/senior-code-review feature/user-auth-refactor`

**Phase 1**: `git diff origin/main...feature/user-auth-refactor` → 12 files changed, +340 / -120.

**Phase 2**: `auth/middleware.ts` modified. Glob finds 14 call sites. Read reveals it enforces role checks on every request. New version adds an `if (process.env.SKIP_AUTH === 'true')` bypass.

**Phase 3 — System Entropy**: `SKIP_AUTH` is a permanent state-space branch. Every future security audit must account for it. TCO multiplier: high.
**Phase 3 — Blast-Radius**: If this env var leaks to production (it has before), the entire auth layer is bypassed. Blast radius: all authenticated routes.
**Phase 3 — Chesterton's Fence**: The prior code had no bypass. What incident or test need created this? Not documented.

**Output**:
```
## Code Review: user-auth-refactor
### Verdict: REQUEST CHANGES

### BLOCK findings
1. auth/middleware.ts:47 — SKIP_AUTH env-var bypass removes auth enforcement
   unconditionally in any environment where the variable is set. No guard on
   NODE_ENV, no audit log on bypass activation. Blast radius: all authenticated
   routes. Rollback requires env-var removal plus deployment.
   [Blast-Radius Reasoning + System Entropy / TCO Accounting]

### WARN findings
1. auth/middleware.ts:47 — No Chesterton justification for why the original
   code lacked a bypass. If this is test-only, move it to test setup, not
   production middleware.

### Mental Model Summary
This change introduces a permanent execution branch that disables a system-wide
invariant (every request is authenticated) via an environment variable. Applying
Blast-Radius Reasoning: a misconfigured deployment silently exposes all routes.
Applying Future-State Simulation: in 3 more changes, SKIP_AUTH will be referenced
in other middleware layers, becoming load-bearing infrastructure that can never be
safely removed.

### Required Actions
1. Remove SKIP_AUTH from production middleware. If test bypass is needed,
   implement it in test fixtures only (e.g., mock the auth module).
2. Add a comment or PR description explaining why a bypass was needed and
   what the safer alternative is.
```
