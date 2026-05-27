# Swiss-Cheese Failure Analysis Reference

Reference document for `forensic-driven-dev`. Load this file when:
- Mapping the causal chain in Phase 5
- Populating the Swiss-Cheese Layer Analysis table in `rca-report.md`
- Distinguishing proximate from root causes in layered systems

---

## Model Overview

The Swiss-cheese model treats a system's defenses as a stack of slices of Swiss cheese. Each slice has holes (latent weaknesses). Normally, holes in one slice are blocked by solid material in the next. A failure propagates when holes across all slices align simultaneously — creating an unobstructed path from hazard to harm.

**Proximate cause:** the final hole in the final slice — the immediate mechanism of failure.  
**Root cause:** the latent condition (or conditions) that created the hole alignment — the *why* behind the cheese.

Patching only the proximate cause leaves all other holes and the underlying latent conditions in place.

---

## Standard Defensive Layer Taxonomy (Web / Backend Systems)

Use this taxonomy to identify which layers existed and how each failed during the incident.

### Layer 1 — Input / Request Validation
- **Defensive purpose:** Reject malformed, oversized, or unexpected input before it enters the system
- **Common failure modes:** Missing validation, incorrect type coercion, unbounded payload size accepted
- **Latent conditions:** Schema evolved without validation update, upstream service changed payload format

### Layer 2 — Application Logic Correctness
- **Defensive purpose:** Correct transformation and state management of data flowing through the service
- **Common failure modes:** Off-by-one, race condition, unbounded data structure growth, incorrect nil/null handling
- **Latent conditions:** Implicit assumption about data cardinality, uncovered edge case in business logic

### Layer 3 — Resource Bounds and Backpressure
- **Defensive purpose:** Prevent resource exhaustion (memory, connections, file descriptors, threads)
- **Common failure modes:** Missing eviction policy, no connection pool maximum, unbounded queue
- **Latent conditions:** Correct under expected load; breaks only at elevated concurrency or data volume

### Layer 4 — Dependency Isolation and Circuit Breaking
- **Defensive purpose:** Contain failures from upstream services; prevent cascading
- **Common failure modes:** No timeout configured, circuit breaker disabled or threshold too high, no retry budget
- **Latent conditions:** Upstream was always fast; timeout assumed unnecessary; circuit breaker never tested

### Layer 5 — Deployment and Change Management
- **Defensive purpose:** Prevent new defects from reaching production; enable fast rollback
- **Common failure modes:** No canary or staged rollout, missing rollback plan, config change not tracked as a change
- **Latent conditions:** Deployment process assumed safe because previous N deployments succeeded

### Layer 6 — Testing and Staging Fidelity
- **Defensive purpose:** Detect defects before production; reproduce production conditions
- **Common failure modes:** Staging uses smaller data set, no soak test, load profile mismatch
- **Latent conditions:** Defect only manifests under sustained load or large data volume — invisible in short tests

### Layer 7 — Observability and Alerting
- **Defensive purpose:** Detect degradation early; enable fast human response
- **Common failure modes:** Alert threshold too high, metric not collected, alert fires but is ignored
- **Latent conditions:** Threshold set at historical maximum rather than operational maximum; alert fatigue

### Layer 8 — Runbook and Incident Response
- **Defensive purpose:** Enable responders to act correctly under pressure
- **Common failure modes:** Runbook missing, outdated, or describes wrong component, no rollback steps
- **Latent conditions:** Runbook not maintained across service evolution

### Layer 9 — Post-Incident Learning
- **Defensive purpose:** Prevent recurrence; propagate learnings to team
- **Common failure modes:** Root cause identified as proximate cause only, remediation addresses symptom not system, no follow-through on long-term items
- **Latent conditions:** Time pressure forces premature close; no retrospective mechanism

---

## Distinguishing Active Failures from Latent Conditions

| Type | Definition | Example |
|------|-----------|---------|
| **Active failure** | An action or omission that directly triggered the incident | Developer committed unbounded cache; deploy pipeline pushed without soak test |
| **Latent condition** | A pre-existing weakness that enabled the active failure to propagate | No memory alert below 90%; staging environment smaller than production; no eviction policy standard |

**Root cause analysis is incomplete if it identifies only active failures.** The latent conditions are what made the system fragile in the first place. Remediation must address both.

---

## Completing the Swiss-Cheese Table

For each layer that failed, populate the table in `rca-report.md`:

```
| Layer              | Defensive Purpose         | How It Failed                        | Latent Condition                          |
|--------------------|--------------------------|--------------------------------------|-------------------------------------------|
| Testing fidelity   | Catch defects before prod | No soak test in staging pipeline     | Staging infra provisioned at 1/4 of prod  |
| Resource bounds    | Prevent memory exhaustion | SessionManager cache has no eviction | No team standard for collection bounds    |
| Alerting           | Early degradation signal  | Memory alert threshold at 90%        | Threshold never reviewed post-migration   |
```

**Minimum one row per slice that had a hole.** If only one layer failed, the Swiss-cheese analysis is incomplete — look deeper.

---

## Recurrence Risk Classification

After completing the layer table, classify recurrence risk:

| Risk Level | Criteria |
|-----------|---------|
| **Low** | Proximate cause fixed; latent conditions remediated; similar pattern has no other instances in codebase |
| **Medium** | Proximate cause fixed; some latent conditions remain; recurrence requires same triggering combination |
| **High** | Only symptom patched; latent conditions still present; triggering conditions likely to recur |
| **Critical** | Symptom not fully mitigated; root cause unknown or contested; blast radius cross-service |

Document the classification and its rationale in `rca-report.md` Section 5.
