# FDD Investigation Protocol Reference

Reference document for `forensic-driven-dev`. Load this file when:
- Generating hypotheses (Phase 3)
- Applying the inversion technique
- Classifying evidence provenance
- Applying the missing-evidence doctrine

---

## Hypothesis Generation Heuristics

### Minimum Hypothesis Set
Before falsification begins, generate at least three hypotheses covering distinct causal categories:

| Category | Question to Answer |
|---------|-------------------|
| **Code change** | Was a deployment, migration, or config change made within 24h of symptom onset? |
| **Resource pressure** | Did a resource (memory, connections, disk, file descriptors) approach or exceed a limit? |
| **External dependency** | Did an upstream service, database, or API degrade or change behavior? |
| **Load / traffic** | Did request volume, data volume, or concurrency change materially? |
| **Temporal / scheduled** | Does the failure pattern correlate with a scheduled job, cron, or time-based trigger? |
| **Environmental drift** | Did the environment (OS, runtime version, certificate, TLS config) change silently? |

Generate at least one hypothesis from three distinct categories before proceeding.

---

### The Inversion Technique
**Use when only one plausible hypothesis exists.**

1. State H1 explicitly: `"The failure was caused by X."`
2. Write its negation: `"The failure was NOT caused by X."`
3. Given the negation, what is the next most parsimonious explanation for the observed evidence?
4. That explanation becomes H2.
5. Repeat for H3.

This forces the investigator off the first plausible path and surfaces competing explanations that would otherwise be invisible.

---

### Hypothesis Quality Criteria
A well-formed hypothesis:
- States a specific mechanism (not "a bug" or "performance issue")
- Is falsifiable — there exists a test that would disprove it
- Predicts additional observable evidence (if H1 is true, we expect to see Y)
- Does not merely restate the symptom

**Poor hypothesis:** "The server ran out of memory."  
**Well-formed hypothesis:** "The `UserSessionManager` introduced in v3.14.1 creates an unbounded in-memory map of active sessions that is never evicted, causing heap growth proportional to concurrent session count."

---

## Evidence Provenance Classification

Classify each piece of evidence before using it to falsify or confirm a hypothesis.

| Class | Description | Trust Weight |
|-------|-------------|-------------|
| **Primary** | Directly observed at the time of the incident (captured logs, live process state, metrics) | High |
| **Secondary** | Reconstructed from durable storage (log archives, APM traces, DB audit logs) | Medium-High |
| **Derived** | Inferred from primary/secondary evidence by applying known system behavior | Medium |
| **Testimonial** | Reported by humans after the fact (incident descriptions, Slack messages) | Low-Medium |
| **Absent** | Evidence that should exist but does not | Treat as active signal |

**Do not accept Derived or Testimonial evidence as sole grounds for closing a hypothesis.**

---

## Missing-Evidence Doctrine

Absence of evidence is not evidence of absence in production forensics. Apply these rules:

1. **If a log gap exists:** the gap itself requires explanation. Was logging disabled? Was the process killed? Did a rotation occur?
2. **If a metric is missing:** was the metric being collected at that time? Was the agent healthy?
3. **If a hypothesis predicts evidence that does not exist:** this is partial falsification — record it and reduce confidence; do not discard unless the absence is itself conclusive.
4. **If critical evidence is permanently unavailable:** document the unavailability in `assumption-audit.md` and carry it as residual uncertainty in `rca-report.md` Section 7.

---

## Commitment Threshold

Do not transition from investigation to remediation until ALL of the following are satisfied:

- [ ] Every hypothesis except one has been actively disproven with specific evidence
- [ ] The surviving hypothesis has at least one direct positive evidence chain
- [ ] The surviving hypothesis explains all anomalies in the timeline — not only the visible symptom
- [ ] The AI assumption audit has been completed
- [ ] All HIGH-risk unverified assumptions are either verified or documented as residual risk

If external pressure forces premature closure before these criteria are met, document the following in `rca-report.md`:
- Which criteria remain unsatisfied
- The specific evidence that was not gathered
- The residual recurrence risk accepted by closing early
- The stakeholder who accepted that risk

---

## Forced Alternative Generation (Extended Inversion)

When analysis has converged on H1 and generating alternatives feels artificial:

**Step 1 — Blame shift:** Assume the failure was caused by a completely different component than H1 suggests. Which component? What would that mechanism look like?

**Step 2 — Timing shift:** Assume the root cause existed for weeks before the symptom appeared. What latent condition would only become visible under specific conditions?

**Step 3 — Scope shift:** Assume the failure affects more than the observed blast radius. What would explain why only part of the system showed symptoms?

Each step should produce a distinct candidate hypothesis. Even if they are later falsified quickly, this exercise prevents the analyst from anchoring exclusively on the first plausible explanation.
