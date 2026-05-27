#!/usr/bin/env python3
"""
fdd_init.py — Forensic-Driven Development Investigation Workspace Initializer

Creates a structured investigation directory under investigations/{incident-id}/
with four pre-populated artifact files. All paths are validated against the
declared project root to prevent writes outside the workspace.

Usage:
    python fdd_init.py --incident-id INC-2024-042 \
                       --symptom "Memory spike at 03:00 UTC causing OOM kill" \
                       --root-dir .

Output (stdout, machine-readable):
    INVESTIGATION_DIR=investigations/INC-2024-042
    INCIDENT_ID=INC-2024-042
    CREATED=investigations/INC-2024-042/timeline.md
    CREATED=investigations/INC-2024-042/hypotheses.md
    CREATED=investigations/INC-2024-042/assumption-audit.md
    CREATED=investigations/INC-2024-042/rca-report.md
    STATUS=READY
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------

def validate_within_root(path: Path, root: Path) -> None:
    """Abort if path resolves outside root."""
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        print(
            f"ERROR: Resolved path {path.resolve()} is outside root {root.resolve()}",
            file=sys.stderr,
        )
        sys.exit(1)


def sanitize_incident_id(raw: str) -> str:
    """Allow only alphanumerics, hyphens, underscores. Collapse runs of disallowed chars."""
    clean = re.sub(r"[^a-zA-Z0-9\-_]", "-", raw.strip())
    clean = re.sub(r"-{2,}", "-", clean).strip("-")
    if not clean:
        print("ERROR: incident-id is empty after sanitization.", file=sys.stderr)
        sys.exit(1)
    if len(clean) > 64:
        print("ERROR: incident-id exceeds 64 characters.", file=sys.stderr)
        sys.exit(1)
    return clean


# ---------------------------------------------------------------------------
# Artifact content generators
# ---------------------------------------------------------------------------

def timeline_content(incident_id: str, symptom: str, now: str) -> str:
    return f"""\
# Timeline — {incident_id}

**Opened:** {now}  
**Symptom:** {symptom}

---

## Volatile Evidence Captured
<!-- Mark each item [CAPTURED: UTC timestamp] when secured. Do not proceed to analysis until all reachable items are captured. -->

- [ ] Process state snapshot (ps/top output)
- [ ] Primary application log tail (last 500 lines)
- [ ] Active deployment manifest / version hashes
- [ ] Active configuration values relevant to the symptom
- [ ] Network connection state (if relevant)
- [ ] Queue / cache depth (if relevant)

---

## Event Log
<!-- Entries in strict chronological order: [TIMESTAMP UTC] SOURCE — EVENT — EVIDENCE_REF -->
<!-- A gap in the timeline is evidence. Record gaps explicitly. -->

| Timestamp (UTC) | Source | Event | Evidence Ref |
|-----------------|--------|-------|--------------|
| {now} | FDD Init | Investigation opened | — |

---

## Earliest Detectable Precursor
<!-- Identify the earliest signal in the log that preceded the visible symptom. -->
> (complete during Phase 2)
"""


def hypotheses_content(incident_id: str, symptom: str, now: str) -> str:
    return f"""\
# Hypothesis Matrix — {incident_id}

**Opened:** {now}  
**Symptom:** {symptom}

---

## Active Hypotheses
<!-- Minimum 3 hypotheses before falsification begins.
     State each as a falsifiable causal claim: "X occurred because Y, which caused Z".
     No hypothesis is 'the cause' until all others are actively disproven. -->

| # | Hypothesis | Confidence | Evidence For | Evidence Against | Status |
|---|-----------|-----------|-------------|-----------------|--------|
| H1 | | 0% | — | — | OPEN |
| H2 | | 0% | — | — | OPEN |
| H3 | | 0% | — | — | OPEN |

---

## Falsification Tests
<!-- For each hypothesis: design the minimum test that would DISPROVE it if it were false.
     Execute the test. Record result. -->

### H1
- [ ] Falsification test: *(describe what would disprove H1)*
  - Result: PENDING

### H2
- [ ] Falsification test: *(describe what would disprove H2)*
  - Result: PENDING

### H3
- [ ] Falsification test: *(describe what would disprove H3)*
  - Result: PENDING

---

## Closure Gate
<!-- A hypothesis may be promoted to root cause only when ALL of the following are true:
     1. All competing hypotheses are actively disproven (not merely deemed unlikely).
     2. At least one positive evidence chain supports the winner.
     3. The winner explains ALL timeline anomalies, not only the visible symptom. -->

- [ ] All competing hypotheses disproven with specific evidence
- [ ] Positive evidence chain exists for the winning hypothesis
- [ ] Winning hypothesis explains all timeline anomalies

---

## Discarded Hypotheses
<!-- Move falsified hypotheses here with the specific evidence that disproved them. -->

| # | Hypothesis | Disproved By | Disproved At |
|---|-----------|-------------|-------------|

---

## Winning Hypothesis
<!-- Complete only after closure gate is fully satisfied. -->
> (pending)
"""


def assumption_audit_content(incident_id: str, symptom: str, now: str) -> str:
    return f"""\
# AI Assumption Audit — {incident_id}

**Opened:** {now}  
**Symptom:** {symptom}

---

## Purpose
Surface assumptions made during investigation that have not been verified against evidence.
Every unverified HIGH-risk assumption is either resolved before closing or documented as residual risk.

---

## Assumption Categories
- **SYSTEM** — about infrastructure, dependencies, resource limits
- **DATA** — about data shape, volume, or expected state
- **CAUSAL** — about what caused what
- **TEMPORAL** — about when events occurred
- **SCOPE** — about what was and was not affected

---

## Assumption Inventory

| # | Assumption | Category | Verified? | Verification Method | Risk if Wrong |
|---|-----------|----------|-----------|-------------------|--------------|
| A1 | | SYSTEM | NO | — | — |
| A2 | | DATA | NO | — | — |
| A3 | | CAUSAL | NO | — | — |

---

## Provenance Gaps
<!-- List data you wish you had but do not have. Missing evidence is itself evidence.
     A gap that cannot be filled must be documented in rca-report.md Section 7. -->

| Gap | Why It Matters | Workaround / Residual Risk |
|-----|---------------|--------------------------|

---

## Premature-Closure Risk
<!-- Is there pressure to close before root cause is verified? Document it explicitly. -->

- Stakeholder pressure: (none / describe)
- Time constraint: (none / describe)
- Decision: (continue / accept residual risk — document rationale below)

**Rationale if accepting residual risk:**
> (none)
"""


def rca_report_content(incident_id: str, symptom: str, now: str) -> str:
    return f"""\
# Root Cause Analysis Report — {incident_id}

**Opened:** {now}  
**Status:** IN PROGRESS  
**Symptom:** {symptom}

---

## 1. Incident Summary
*(Complete when investigation closes)*

**Proximate Cause:**
> TBD — the immediate trigger of the visible symptom

**Root Cause:**
> TBD — the deepest verified condition that, if absent, prevents the failure

**Contributing Conditions:**
> TBD — latent factors that increased vulnerability

---

## 2. Swiss-Cheese Layer Analysis
<!-- Each row = one defensive layer that existed but failed to stop propagation.
     The proximate cause is the last hole in the last slice.
     The root cause is the latent condition that allowed holes to align. -->

| Layer | Defensive Purpose | How It Failed | Latent Condition |
|-------|------------------|--------------|-----------------|

---

## 3. Timeline Summary
*(Condensed from timeline.md — key events only)*

| Time | Event |
|------|-------|

---

## 4. Evidence Inventory

| Evidence | Source | Confidence | Notes |
|----------|--------|-----------|-------|

---

## 5. Recurrence Risk Assessment

- **Likelihood without intervention:** (Low / Medium / High)
- **Blast radius:** (isolated / service-wide / cross-service / multi-tenant)
- **Systemic contributors still present:** (list any latent conditions not yet remediated)

---

## 6. Remediation

### Immediate — symptom mitigation
- [ ] 

### Short-term — proximate cause fix
- [ ] 

### Long-term — root cause and recurrence prevention
- [ ] 

---

## 7. Open Questions and Residual Risk
*(Unresolved unknowns at close — explicitly document what is not known)*

| Question | Risk if Unresolved | Owner | Target Date |
|---------|-------------------|-------|------------|

---

**Closed:** *(UTC timestamp)*  
**Closed by:** *(analyst)*  
**Final Status:** *(RESOLVED / CLOSED-WITH-RESIDUAL-RISK)*
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize an FDD investigation workspace."
    )
    parser.add_argument("--incident-id", required=True, help="Short incident identifier")
    parser.add_argument("--symptom", required=True, help="One-sentence symptom description")
    parser.add_argument(
        "--root-dir", default=".", help="Project root directory (default: current dir)"
    )
    args = parser.parse_args()

    root = Path(args.root_dir).resolve()
    if not root.exists():
        print(f"ERROR: root-dir does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    incident_id = sanitize_incident_id(args.incident_id)
    symptom = args.symptom.strip()[:500]  # cap to prevent absurdly long file headers
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    inv_dir = root / "investigations" / incident_id
    validate_within_root(inv_dir, root)

    if inv_dir.exists():
        print(
            f"WARNING: Investigation directory already exists — resuming: {inv_dir.relative_to(root)}",
            file=sys.stderr,
        )

    inv_dir.mkdir(parents=True, exist_ok=True)

    artifacts = {
        "timeline.md": timeline_content(incident_id, symptom, now),
        "hypotheses.md": hypotheses_content(incident_id, symptom, now),
        "assumption-audit.md": assumption_audit_content(incident_id, symptom, now),
        "rca-report.md": rca_report_content(incident_id, symptom, now),
    }

    created = []
    for filename, content in artifacts.items():
        filepath = inv_dir / filename
        validate_within_root(filepath, root)
        if not filepath.exists():
            filepath.write_text(content, encoding="utf-8")
            created.append(filepath.relative_to(root))
        else:
            created.append(f"{filepath.relative_to(root)} (skipped — already exists)")

    # Machine-readable output for SKILL.md to parse
    print(f"INVESTIGATION_DIR={inv_dir.relative_to(root)}")
    print(f"INCIDENT_ID={incident_id}")
    for path in created:
        print(f"CREATED={path}")
    print("STATUS=READY")


if __name__ == "__main__":
    main()
