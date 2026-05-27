---
name: forensic-driven-dev
description: Runs a structured forensic root-cause investigation on production incidents, persistent bugs, and unexpected system behaviors. Applies crime-scene preservation, timeline reconstruction, multi-hypothesis falsification, Swiss-cheese failure analysis, and AI assumption auditing to reach verified root causes — not proximate symptoms. Use when diagnosing a production incident, tracing a recurring bug, investigating OOM kills, performance regressions, data corruption, or conducting post-mortems. Do NOT use for routine code review, new feature work, or shallow one-shot debugging where root cause is already confirmed.
disable-model-invocation: true
allowed-tools: Read Bash Grep Glob
argument-hint: "[incident-id] [symptom description]"
---

## Purpose

Encode the Forensic-Driven Development (FDD) discipline: distinguish verified root causes from proximate symptoms by applying systematic evidence gathering, multi-hypothesis falsification, and layered failure analysis.

**Core anti-pattern being corrected:** symptom fixation — patching the visible failure while leaving the causal chain, systemic contributors, and recurrence risk unresolved.

**Core heuristic:** when a plausible local cause appears, treat it as H1 and generate at least two alternative hypotheses before investigating any of them further. Production failures frequently emerge from layered latent conditions interacting across time.

---

## Inputs

- `$ARGUMENTS` — invocation string; first space-separated token is the incident ID, remainder is the symptom description
- Codebase, logs, config files, and deployment manifests reachable via allowed tools
- Additional context pasted directly into the conversation

---

## Phase 0 — Workspace Initialization

Parse `$ARGUMENTS`:
- Token 0 → incident ID (e.g., `INC-2024-042`)
- Tokens 1+ → symptom description

Run the initialization script:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/fdd_init.py" \
  --incident-id "$(echo $ARGUMENTS | awk '{print $1}')" \
  --symptom "$(echo $ARGUMENTS | cut -d' ' -f2-)" \
  --root-dir "."
```

Confirm `STATUS=READY` in stdout. Read the `INVESTIGATION_DIR=` value — all artifacts are written there.

---

## Phase 1 — Crime-Scene Preservation

**Execute before any analysis. Volatile evidence degrades or disappears.**

Capture and record in `timeline.md` under "Volatile Evidence Captured":

1. Process state: `bash ps aux --sort=-%mem 2>/dev/null | head -40`
2. Recent log tail: read the 500 most recent lines of the primary application log
3. Active deployment version: read `package.json`, `pyproject.toml`, `Cargo.toml`, or equivalent; record exact version hashes
4. Active configuration: read env config files; record values relevant to the symptom
5. Network state (if relevant): `bash ss -tunapl 2>/dev/null | head -60`

Mark each item `[CAPTURED: {UTC timestamp}]` in `timeline.md`.

**Do not proceed to Phase 2 until all reachable volatile evidence is captured.**

---

## Phase 2 — Timeline Reconstruction

Reconstruct the chronological event sequence leading to the symptom.

1. Identify all relevant log sources: `glob **/*.log`, `glob **/logs/**`
2. Search for anomalies, errors, warnings, and state changes in ±2 hours around first observation
3. Record each event: `[TIMESTAMP UTC] SOURCE — EVENT — EVIDENCE_REF`
4. **Explicitly record gaps** — a gap in the timeline is evidence, not silence
5. Identify the earliest detectable precursor; it is typically closer to the root cause than the visible failure

---

## Phase 3 — Hypothesis Generation

**Minimum 3 hypotheses must exist before falsification begins.**

For each hypothesis, populate a row in `hypotheses.md`:

- State it as a falsifiable causal claim: `"X occurred because Y, which caused Z"`
- Assign initial confidence 0–100%
- List existing evidence for and against
- Set status OPEN

Apply the inversion technique if only one hypothesis exists: assume it is wrong and write the alternative that would explain why. See `${CLAUDE_SKILL_DIR}/references/investigation-protocol.md` for generation heuristics.

---

## Phase 4 — Multi-Hypothesis Falsification

For each OPEN hypothesis:

1. Design the minimum test that would **disprove** it if it were false
2. Execute using Read, Grep, Bash, or Glob
3. Record test + result in `hypotheses.md`
4. If disproven: move to Discarded Hypotheses with the specific disproving evidence
5. If not disproven: raise confidence; do not close the investigation

**Closure gate:** A hypothesis may be promoted to root cause only when:
- All competing hypotheses are actively disproven (not merely deemed unlikely)
- At least one positive evidence chain supports the winner
- The winner explains ALL timeline anomalies, not only the visible symptom

---

## Phase 5 — Swiss-Cheese Failure Analysis

After the winning hypothesis is identified, map the full causal chain.

For each defensive layer that existed but failed to prevent propagation, add a row to the Swiss-Cheese Layer Analysis table in `rca-report.md`:

- Layer name (input validation, circuit breaker, alerting threshold, etc.)
- Its defensive purpose
- How it failed or was bypassed in this incident
- The latent condition that pre-existed

See `${CLAUDE_SKILL_DIR}/references/swiss-cheese-analysis.md` for layer taxonomy.

**The proximate cause is the last hole in the last slice. The root cause is the latent condition that allowed holes to align.**

---

## Phase 6 — AI Assumption Audit

Enumerate every assumption made during investigation in `assumption-audit.md`:

1. What assumptions did this analysis make about system behavior, data state, timing, or causality?
2. Which are verified against evidence? Which are not?
3. What data is missing that would change the conclusion if it existed?
4. Is there premature-closure pressure? Document it explicitly.

For each unverified assumption with HIGH risk if wrong: either verify before closing or record as residual risk in `rca-report.md` Section 7.

---

## Phase 7 — Root Cause Verdict

Complete `rca-report.md`:

1. **Proximate Cause** — immediate trigger of the visible symptom
2. **Root Cause** — deepest verified condition that, if absent, prevents the failure
3. **Contributing Conditions** — latent factors that increased vulnerability
4. **Recurrence Risk** — likelihood and blast radius without intervention
5. **Remediation** — three tiers: immediate (symptom), short-term (proximate), long-term (root + systemic)
6. **Open Questions** — unresolved unknowns with documented residual risk

---

## Safety Rules

- Never patch the visible symptom without completing at least Phase 4
- Never close the investigation while competing hypotheses remain unfalsified
- Treat the first plausible cause as H1, not as the answer
- Record missing evidence explicitly — absence is evidence
- Refuse to confirm a root cause that does not explain all timeline anomalies
- If stakeholder pressure demands premature closure, document it in `assumption-audit.md` and state residual risk explicitly in `rca-report.md`

---

## Output Artifacts

| File | Phases | Contains |
|------|--------|---------|
| `investigations/{id}/timeline.md` | 0, 1, 2 | Volatile evidence log, chronological event sequence |
| `investigations/{id}/hypotheses.md` | 3, 4 | All hypotheses, falsification tests, discards |
| `investigations/{id}/assumption-audit.md` | 6 | Assumptions, provenance gaps, closure-risk declaration |
| `investigations/{id}/rca-report.md` | 5, 7 | Proximate/root cause, Swiss-cheese layers, remediation plan |

---

## Verification

```bash
INCIDENT_ID="<your-id>"

# All four artifact files exist
ls investigations/${INCIDENT_ID}/

# RCA report has a non-empty root cause section
grep -A 3 "Root Cause" investigations/${INCIDENT_ID}/rca-report.md

# No OPEN hypotheses remain at close
grep "OPEN" investigations/${INCIDENT_ID}/hypotheses.md \
  && echo "WARNING: open hypotheses remain — investigation not complete"

# At least one volatile evidence item was captured
grep "\[CAPTURED:" investigations/${INCIDENT_ID}/timeline.md
```

---

## Troubleshooting

**Script fails with `path outside root` error**
Cause: `--root-dir` resolved differently than cwd.
Fix: Run from project root or pass `--root-dir "$(pwd)"` explicitly.

**No log files found during Phase 2**
Cause: Non-standard log paths or rotated/deleted logs.
Fix: Record in `assumption-audit.md` as a provenance gap; note explicitly in `rca-report.md` Section 7; continue with available evidence.

**Only one plausible hypothesis exists**
Cause: Symptom-fixation bias; analyst converged prematurely.
Fix: Apply the inversion technique from `references/investigation-protocol.md`. Assume H1 is false; write the hypothesis that explains why.

**Competing hypothesis cannot be falsified with available tools**
Cause: Required evidence is inaccessible (external service, deleted log, locked environment).
Fix: Mark UNVERIFIABLE in `hypotheses.md`. Record inaccessibility in `assumption-audit.md`. State residual uncertainty in `rca-report.md`.

**Investigation exceeds session context**
Cause: Large log corpus or long timeline.
Fix: Summarize each phase's findings into the artifact files before continuing. The files serve as persistent state across sessions.

---

## Worked Example

**Invocation:** `/forensic-driven-dev INC-2024-042 Memory spike at 03:00 UTC causing OOM kill on web-01`

**Phase 0:** Script creates `investigations/INC-2024-042/` with all four starter files.

**Phase 1:** ps snapshot shows Ruby worker at 8.2 GB. Log tail: `GC overhead limit exceeded` at 02:58. Deploy manifest: v3.14.1 deployed at 01:45.

**Phase 2:** Timeline — 01:45 deploy → 02:30 memory climb begins → 02:58 GC pressure → 03:01 OOM kill. Gap: no alerts between 02:30 and 02:58.

**Phase 3:** H1: memory leak in v3.14.1. H2: traffic spike exceeded baseline. H3: external dependency holding open connections. H4: GC tuning parameter changed in deploy.

**Phase 4:** H2 falsified (traffic metrics flat). H3 falsified (connection pool normal). H4 falsified (deploy diff shows no JVM flags changed). H1 survives: diff reveals unbounded cache in `UserSessionManager`.

**Phase 5:** Swiss-cheese layers: no soak test in staging, memory alert threshold set at 90%, unbounded collection not flagged in code review.

**Phase 6:** Unverified assumption surfaced: staging environment memory profile assumed equal to production.

**Phase 7:** Root cause — unbounded `UserSessionManager` cache in v3.14.1 propagated by absent soak testing. Remediation: immediate rollback; LRU-bounded cache; add soak test to CI gate; lower memory alert to 70%.
