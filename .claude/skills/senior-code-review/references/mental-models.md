# Mental Models Reference

Five mental models applied in Phase 3 of every review. Each targets a class of defect that diff-only analysis systematically misses.

---

## 1. Diff-as-System-Perturbation

**Core claim**: A code change is a perturbation applied to a running system with existing invariants. The review question is not "does the new code look reasonable?" but "what contracts does this change assert, silently relax, or break in the system as a whole?"

**Application protocol**:
1. Enumerate invariants present in the unchanged code surrounding the diff: preconditions, postconditions, thread-safety assumptions, resource ownership, ordering dependencies.
2. For each changed symbol, determine whether the new code **preserves**, **strengthens**, **weakens**, or **silently violates** those invariants.
3. Specifically inspect: return-value semantics changes, null/nil/None handling, exception propagation path changes, resource lifecycle (open/close, acquire/release), and idempotency assumptions.

**Where this fires**:
- A function that previously always returned a non-null value now can return null in one path — all callers assume non-null.
- A method that was idempotent now has a side effect on second call — callers in retry loops break.
- A previously synchronous function is now async — call sites must await but may not.

**Verdict implication**: A change that looks locally correct but relaxes an invariant relied upon by callers is a **BLOCK** if callers are not updated, a **WARN** if callers are updated but the invariant change is not documented.

---

## 2. System Entropy / TCO Accounting

**Core claim**: Every added code path, branch, flag, or conditional is a **state-space multiplier and entropy accumulator**. The question is not "is this readable?" but "what is the total lifecycle cost of maintaining every execution path this PR introduces?"

**Application protocol**:
1. Count distinct execution paths added: each `if`, `switch` case, early return, exception handler, feature flag check, and async branch.
2. Estimate maintenance cost: who must understand each path in 18 months? How many tests are required to cover the cross-product?
3. Apply TCO accounting: temporary flags become permanent when they outlive their rollout window. Temporary branches become permanent when the author who understood them leaves.
4. Ask: does the added complexity correspond to a commensurate reduction in complexity elsewhere, or is it net additive?

**Where this fires**:
- A feature flag added "temporarily for the experiment" — experiments persist; flags rarely die.
- A third parameter added to a function that already has two optional parameters — combinatorial test surface grows as n³.
- Business logic embedded in a hot path: every future change to that logic requires touching performance-sensitive code.

**Verdict implication**: Unjustified entropy addition is a **WARN**. Entropy added to a hot path or a frequently-modified module is a **BLOCK** if no TCO justification is provided.

---

## 3. Future-State Simulation

**Core claim**: Code is a template for future changes. Evaluate the PR not in isolation but as the first instance of a pattern that will be applied repeatedly.

**Application protocol**:
1. Mentally apply three additional changes of the same type: another flag, another branch, another parameter, another exception handler, another caller.
2. Ask: does the structure remain coherent after three iterations, or does it collapse into unmaintainable complexity?
3. Identify missing abstractions: what grouping, interface, or indirection would make the next three changes safe, local, and independently testable?

**Where this fires**:
- A switch statement gains a fourth case — five more cases will follow, and the switch will not be extracted.
- A second optional parameter added — a third is coming, and they will interact.
- An if/else added to route between two implementations — a registry or strategy pattern is the missing abstraction.

**Verdict implication**: A change that is internally clean but makes the next change harder or more error-prone is an architectural regression. **WARN** if the pattern is nascent; **BLOCK** if the pattern is already established and this PR deepens it without introducing the missing abstraction.

---

## 4. Chesterton's Fence in Code

**Core claim**: Before removing or changing existing code, the reviewer must understand *why it was written that way*. Code that looks wrong or redundant may encode a hard-won invariant, a platform quirk, a past incident fix, or a compliance requirement.

**Application protocol**:
1. For every deletion of >5 lines, or every behavioral change to existing logic: identify whether this was a deliberate design choice. Evidence: comments, tests exercising the deleted path, linked issues, git blame.
2. If the PR description does not justify the removal or behavioral change, treat the PR as incomplete at those locations.
3. Sources of evidence: git log on deleted lines, issue tracker, incident postmortems, test names.

**Where this fires**:
- A retry loop "simplified" by removal — the original retry was encoding a real transient failure rate.
- A null check removed as "unnecessary" — it was guarding against a race condition in a specific deployment topology.
- A fallback path deleted because "we never hit it" — it was the blast-radius boundary for a failure mode that has not recurred yet.

**Verdict implication**: Deletion without documented justification is a hypothesis that the deleted code was wrong. That hypothesis requires evidence. Missing justification is a **WARN**; deletion of safety-critical paths without evidence is a **BLOCK**.

---

## 5. Blast-Radius Reasoning

**Core claim**: A change must be evaluated not only for correctness under normal conditions but for its behavior under failure, and for the scope of that failure's propagation.

**Application protocol**:
1. **Scope**: Which callers, downstream services, users, or data stores are affected by a malfunction in the changed code?
2. **Rollback safety**: Can the change be reverted in production without data migration, schema incompatibility, or state corruption?
3. **Observability**: Does the change emit sufficient logging, metrics, or traces to diagnose a production failure within an acceptable MTTD window?
4. **Failure boundaries**: Are there circuit breakers, retries with backoff, error boundaries, or fallbacks around new I/O paths, external calls, or database writes?
5. **Staged exposure**: For high-risk changes, is there a feature flag, canary, or percentage rollout mechanism?

**Where this fires**:
- A new database write in the hot path with no error handler — failure silently corrupts or drops requests.
- A synchronous external service call with no timeout — one slow dependency cascades to all threads.
- A schema migration that drops a column used by a still-deployed old version — rollback causes crashes.
- A change to a shared utility function used by 40 call sites — a regression has blast radius 40.

**Verdict implication**: Wide blast radius + no new observability = **BLOCK** for production-facing changes. Missing circuit breaker on a new I/O path = **WARN** minimum, **BLOCK** if the service is on the critical path.
