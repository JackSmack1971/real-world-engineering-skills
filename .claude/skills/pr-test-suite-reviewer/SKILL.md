---
name: pr-test-suite-reviewer
description: Evaluates pull request test suites as adversarial probes against
  system-level behavioral contracts, not proof-of-work for touched lines. Applies
  Blast Radius Mapping, Invariant Preservation and Falsification, Behavioral
  Contract and Encapsulation Boundary reasoning, Suite Health Economics, and BVA
  plus ECP Risk Partitioning to identify gaps in unit, integration, regression,
  and edge-case coverage. Use when asked to review PR tests, audit test coverage,
  assess test quality, design missing tests for a PR, check whether tests provide
  durable confidence, or evaluate a test suite before merge. Corrects the locality
  fallacy: localized code changes verified by mocked call choreography are
  insufficient evidence of system safety. Do NOT use for general code review,
  style linting, or coverage-percentage queries.
allowed-tools: Read Glob Bash
---

# PR Test-Suite Review: Adversarial Contract Analysis

## Epistemic Stance

Every PR is a perturbation. Treat the test suite as a falsification attempt
against the system's preserved invariants — not a completion certificate for
changed lines.

Weight real SoT behavior and observable outcomes over mocked call choreography.
Tests must survive valid implementation changes; they must fail on contract
violations.

**Core rejection — the Locality Fallacy**: localized change + verified mechanics
≠ system safety. A PR that touches AuthService.login() and adds three unit tests
for AuthService has not demonstrated safety for every downstream consumer that
depends on its behavioral contract.

---

## Phase 0: Context Fork (Execute Before Any Analysis)

Fork context. Do not inject raw file content into the main reasoning flow.
Run the following in an isolated sub-agent or bash block, stashing distilled
artifacts to `/tmp/pr-review/`.

```bash
mkdir -p /tmp/pr-review

# Discover changed files
git diff HEAD~1 --name-only > /tmp/pr-review/changed_files.txt
git diff HEAD~1 --stat      > /tmp/pr-review/diff_stat.txt

# Discover test inventory
find . \( -name "*.test.*" -o -name "*.spec.*" -o -path "*/tests/*" \) \
  ! -path "*/node_modules/*" ! -path "*/.git/*" \
  | head -80 > /tmp/pr-review/test_inventory.txt

# Discover public interface changes
grep -rn "^export\|^public\|^module.exports" \
  $(cat /tmp/pr-review/changed_files.txt) 2>/dev/null \
  > /tmp/pr-review/public_symbols.txt
```

Inject only stashed artifacts into main context:

```
!cat /tmp/pr-review/changed_files.txt
!cat /tmp/pr-review/public_symbols.txt
!cat /tmp/pr-review/test_inventory.txt
```

> **Governance note:** If PreToolUse hooks are active, Bash execution is
> scoped to `/tmp/pr-review/` writes and `git diff` reads. No destructive
> commands are issued.

---

## Five Analytical Frameworks

### F1 — Blast Radius Mapping

Enumerate all consumers of every changed public interface, exported symbol, or
shared state mutation.

**Execute for each symbol in `public_symbols.txt`:**
```bash
grep -rn "$MODULE" --include="*.ts" --include="*.js" --include="*.py" \
  --include="*.go" --include="*.rb" . \
  | grep -v "node_modules\|\.git\|$MODULE itself" \
  > /tmp/pr-review/blast_radius_raw.txt
```

Map: Changed Symbol → Direct Callers → Transitive Callers (depth ≤ 2) →
External Consumer (service boundary).

Flag every consumer with no corresponding test in `test_inventory.txt`.

**Output artifact:** Blast Radius table (Section 1 of review output).

---

### F2 — Invariant Preservation + Falsification

For each public interface and shared state mutation in the diff, enumerate
behavioral contracts that must hold post-PR.

**Invariant sources — check all:**
- Public API signatures and return shapes
- Shared state pre/post conditions (DB rows, cache entries, event sequences)
- Error propagation contracts (thrown types, status codes, error message shapes)
- Ordering and idempotency guarantees

**Falsification test:** Does the test suite contain ≥1 test that would **FAIL**
if the invariant were silently violated? If no: **INVARIANT GAP**.

Status values: `COVERED` / `INVARIANT GAP` / `PARTIAL`.

---

### F3 — Behavioral Contract vs. Structural Lock-In

For each test in the PR, classify:

- **CONTRACT-ANCHORED**: Test asserts on observable output, return value, state
  change, or error thrown. Survives a valid refactor.
- **STRUCTURAL LOCK-IN**: Test asserts on internal call order, mock invocation
  counts, or private method behavior without asserting on observable outcomes.
  Breaks on valid refactors; does not detect contract violations.

**Lock-in signals:**
- `spy.calledWith(...)` or `mock.toHaveBeenCalledTimes(N)` with no output assertion
- Assertions on internal event sequences without asserting on final state
- Tests that pass when the return value is changed to an incorrect but "similar" value

Flag lock-in tests with recommended contract-anchored replacement.

---

### F4 — Suite Health Economics

Score each identified gap on two axes:

| Axis | 1 — Low | 2 — Medium | 3 — High |
|------|---------|-----------|---------|
| **Failure Probability** | Edge case, rarely hit | Occasional under normal load | Likely under normal usage |
| **Blast Impact** | Isolated, single module | Service boundary | Cross-service / data integrity / security |

**Priority = Failure Probability × Blast Impact**

- Priority **≥ 6**: CRITICAL — block PR or require test before merge
- Priority **4–5**: HIGH — require test or written risk acceptance in PR description
- Priority **≤ 3**: LOW — document as known gap; optional

---

### F5 — BVA + ECP Risk Partitioning

For each changed function that processes input values, partition inputs into
equivalence classes and identify boundary values.

**ECP classes to audit — always check:**
- Empty / null / undefined / None
- Single-element vs. multi-element collections
- Numeric: zero, negative one, max safe integer, overflow boundary
- String: empty string, whitespace-only, max declared length, Unicode edge chars
- Boolean: both `true` and `false` explicitly exercised
- Error/rejection path: each distinct error branch

**BVA rule:** Test at `boundary − 1`, `boundary`, and `boundary + 1` for every
numeric or length constraint.

Flag each missing ECP class or boundary value.

---

## Execution Workflow

Execute in order. Do not skip steps.

1. **Ingest**: Read `$ARGUMENTS` for PR identifier, branch, or file list. If
   absent, Phase 0 runs automatically to discover changed files.
2. **Blast Radius**: Apply F1. Produce blast_radius table. Identify uncovered consumers.
3. **Invariant Audit**: Apply F2. Mark each invariant COVERED / GAP / PARTIAL.
4. **Contract Scan**: Apply F3. Tag each PR test CONTRACT-ANCHORED or LOCK-IN.
5. **Health Scoring**: Apply F4. Score every gap. Produce priority table.
6. **BVA/ECP Gaps**: Apply F5. List missing classes and boundaries per changed function.
7. **Emit Review**: Produce the output schema below. No raw file content. Distilled
   findings only.

---

## Output Format

Emit this schema exactly. Write "None identified" if a section is genuinely empty.
Do not emit raw diffs, full file contents, or CI logs.

```
## PR Test-Suite Review: [$ARGUMENTS or auto-detected branch]

### 1. Blast Radius Summary
| Symbol | Caller Depth | PR Test Present | Risk Score |
|--------|-------------|-----------------|------------|

### 2. Invariant Gaps
| Invariant | Status | Consequence if Violated |
|-----------|--------|------------------------|

### 3. Structural Lock-In Tests (Anti-Pattern)
| Test Name | Lock-In Reason | Recommended Contract Replacement |
|-----------|---------------|----------------------------------|

### 4. Suite Health Priority Table
| Gap | Failure Prob | Blast Impact | Priority | Recommendation |
|-----|-------------|-------------|---------|----------------|

### 5. BVA/ECP Missing Coverage
| Function | Missing Class or Boundary | Suggested Assertion |
|----------|--------------------------|---------------------|

### 6. Verdict
CONFIDENCE: HIGH / MEDIUM / LOW / BLOCK
Rationale: [2–3 sentences referencing system-level behavior, not line count]

### 7. Minimum Test Additions to Reach MEDIUM Confidence
[Numbered list: each item states — function under test, input value(s),
expected observable output or state, invariant being probed]
```

---

## Anti-Pattern Recognition

| Anti-Pattern | Signal | Correction |
|---|---|---|
| **Locality Fallacy** | "All touched lines have tests" presented as safety evidence | Require F1 blast radius + F2 invariant coverage before accepting |
| **Structural Lock-In** | Assertions on `spy.calledWith` with no output assertion | Rewrite to assert on observable return value or state |
| **Mock Saturation** | >60% of assertions are on mock call counts | Replace with real SoT integration or explicit contract test |
| **Happy-Path Tunnel** | Zero tests for error paths, null inputs, or boundary values | Apply F5 ECP/BVA partitioning; add one test per missing class |
| **Regression Theater** | Tests pass CI but were written to match current (possibly incorrect) behavior | Inject deliberate regression; verify test fails. If it does not: gap. |

---

## Worked Example

**Input:** `$ARGUMENTS` = PR modifying `UserRepository.findByEmail(email: string)`
to add case-insensitive matching.

**Step 2 — Blast Radius:** 4 callers found: `AuthService`, `ProfileController`,
`InviteService`, `AuditLog`. PR tests cover `AuthService` only.

**Step 3 — Invariant Audit:** Invariants: (a) null for unknown email — COVERED;
(b) single User for exact match — COVERED; (c) case-insensitive match — PARTIAL
(lowercase only); (d) no partial-string match — INVARIANT GAP. `InviteService`
and `AuditLog` callers: no test present.

**Step 4 — Contract Scan:** Existing test mocks DB call order without asserting
return value → **STRUCTURAL LOCK-IN**.

**Step 5 — Health Score:** `InviteService` gap: Prob 2 × Impact 3 = **Priority 6
— CRITICAL**. `AuditLog` gap: Prob 1 × Impact 2 = Priority 2 — LOW.

**Step 6 — BVA/ECP:** Missing: null email, whitespace-only string,
`"Ä@domain.com"` (Unicode), `"USER@DOMAIN.COM"` (all-caps).

**Output — Verdict:** `CONFIDENCE: LOW`
Rationale: Core invariant coverage is partial; a critical downstream consumer
(InviteService) has no test against the new case-insensitive contract. The one
existing structural-lock-in test would survive a regression that returns the
wrong User object.

**Section 7 — Minimum Additions:**
1. `findByEmail` called with `null` — expected: returns `null`, not throws
2. `findByEmail` called with `"USER@DOMAIN.COM"` — expected: returns the correct User record
3. `InviteService.sendInvite` called with a mixed-case email address — expected: invite is delivered successfully
4. `findByEmail` called with `"  user@domain.com  "` (leading/trailing whitespace) — expected: behavior is explicitly defined and asserted (either trims and matches, or returns null consistently)

---

## Troubleshooting

**T1: No test files found for changed modules**
Cause: Non-standard naming (`_test.go`, `Test*.java`) or separate `/tests` tree.
Fix: Broaden discovery: `find . -name "*test*" -o -name "*spec*" -o -name "*Test*"`.
If none exist for changed modules: emit `CONFIDENCE: BLOCK` — "No test
infrastructure present for changed modules; behavioral contract unverifiable."

**T2: Blast radius grep returns hundreds of callers (large monorepo)**
Cause: Highly shared utility changed.
Fix: Scope to first-degree callers only. Add to Section 1: "Transitive blast
radius unaudited — recommend integration test at nearest service boundary."
Apply F4 to the first-degree gap set only; flag transitive risk explicitly.

**T3: Invariants cannot be determined from diff alone**
Cause: Diff shows implementation changes; no interface docs, types, or contracts
define expected behavior.
Fix: Run `grep -n "interface\|type\|@contract\|@throws\|@returns\|raises" $FILE`
on changed files. If still opaque: emit `CONFIDENCE: LOW` — "Invariants
undocumented; falsification adequacy of tests cannot be assessed."

**T4: All tests green in CI; stakeholder claims review is unnecessary**
Cause: Confusion between non-regression and contract coverage.
Fix: Apply Regression Theater check. For one CRITICAL invariant gap, ask: "If I
change the return value of this function to `null` unconditionally, does any test
fail?" If no: test suite provides non-regression theater, not contract coverage.
Document finding in Section 6 rationale.

---

## Verification Checklist

After emitting the review artifact, confirm all are true before delivering:

- [ ] Blast radius table has ≥1 row per changed public symbol
- [ ] Every INVARIANT GAP in Section 2 maps to a specific, numbered test spec in Section 7
- [ ] Verdict rationale references observable system behavior — not line count or coverage %
- [ ] No raw file content, full diffs, or CI logs appear in the emitted output
- [ ] Section 7 test specs each state: function under test, concrete input value(s),
      expected observable output or state, and invariant being probed
