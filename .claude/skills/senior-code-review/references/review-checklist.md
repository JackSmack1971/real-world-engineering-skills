# Review Checklist

Score every item. Assign **BLOCK**, **WARN**, or **NOTE** to each failure. Every BLOCK requires a `file:line-range` citation.

---

## Correctness

| # | Check | Notes |
|---|---|---|
| C1 | Every new code path has a corresponding test (unit or integration). | Documentation-only changes exempt. |
| C2 | Edge cases handled: null/nil/None/empty/zero/overflow/max-value for all inputs. | Focus on public API and I/O boundaries. |
| C3 | Concurrency: no new unsynchronized mutations to shared mutable state; no TOCTOU races. | Especially in async/await, goroutine, or multi-thread contexts. |
| C4 | Error propagation is correct: errors are not silently swallowed; error types are not widened incorrectly. | Check catch-all handlers that discard error detail. |
| C5 | Invariants identified in Phase 2 are preserved by the change. | Cross-reference Phase 2 notes. |
| C6 | Type contracts honored: no implicit coercions, no unsafe casts, no `any` / untyped escape hatches added. | |
| C7 | Resource lifecycle correct: files, connections, and locks are released on all paths including error paths. | |

---

## Readability

| # | Check | Notes |
|---|---|---|
| R1 | Names (variables, functions, types, modules) are accurate to the post-change behavior. | Renamed behavior without renamed identifiers is a readability BLOCK. |
| R2 | Complexity added is proportional to the problem being solved. | Apply Future-State Simulation. |
| R3 | Comments explain *why*, not *what*. No stale comments left from the old behavior. | |
| R4 | No dead code, commented-out code, or debug artifacts (print, console.log, TODO). | |
| R5 | A new team member can locate the primary decision point within 2 minutes of reading the changed file. | If not, the structure needs improvement. |
| R6 | Magic numbers and magic strings are named constants with explanatory names. | |

---

## Architecture

| # | Check | Notes |
|---|---|---|
| A1 | The change does not increase coupling between modules that should remain independent (e.g., domain importing infrastructure directly). | |
| A2 | New abstractions are load-bearing: used in ≥2 places, or required for testability. | Single-use abstractions add complexity without payoff. |
| A3 | No premature generalization: complexity added in anticipation of unconfirmed requirements. | YAGNI applies; flag unless a concrete follow-on is in the tracker. |
| A4 | Layering is respected: business logic does not leak into infrastructure; data access does not leak into presentation or API layers. | |
| A5 | Future-State Simulation applied: structure remains coherent after three more changes of this pattern. | |
| A6 | Dependency direction is correct: lower layers do not import upper layers; no circular dependencies introduced. | |

---

## Security

| # | Check | Notes |
|---|---|---|
| S1 | No secrets, credentials, tokens, or PII hardcoded in source or test files. | Check comments and string literals. |
| S2 | All external inputs (HTTP, CLI args, env vars, file paths, query params) are validated and sanitized before use. | |
| S3 | Authentication and authorization checks are not bypassed, relaxed, or short-circuited by any new code path. | Especially in middleware and route handlers. |
| S4 | New dependencies: check for known CVEs in the package version being added. | Run `npm audit`, `pip-audit`, `trivy`, or equivalent. |
| S5 | SQL and query construction uses parameterized statements; no string interpolation into queries. | |
| S6 | Cryptographic operations use approved libraries; no homebrew crypto; key lengths and algorithms meet current standards. | |
| S7 | No path traversal: file paths constructed from user input are confined to a validated root. | |
| S8 | No arbitrary code execution from user-controlled input: no `eval`, no dynamic `import`, no `exec` with user data. | |

---

## Performance

| # | Check | Notes |
|---|---|---|
| P1 | No N+1 query patterns in hot paths: loops that issue one query per iteration must be rewritten as batch queries. | |
| P2 | No unbounded loops, unbounded recursion, or unbounded memory allocation over external data volumes. | |
| P3 | New caching: cache invalidation strategy is defined; stale cache scenarios are handled. | Cache without invalidation is a latent bug. |
| P4 | Changes to latency-critical paths include a comment citing benchmark evidence or a linked performance test. | |
| P5 | No synchronous blocking I/O in async contexts (blocking a thread pool with file reads, DNS, etc.). | |

---

## Rollback Safety

| # | Check | Notes |
|---|---|---|
| RB1 | Schema changes are backward-compatible (additive only: new nullable columns, no renames, no drops) OR a migration plan with backward-compatibility window is provided. | BLOCK if a deployed old version would crash against the new schema. |
| RB2 | High-risk changes are gated behind a feature flag with a defined off-state. | Off-state must be the safe, prior behavior. |
| RB3 | The change can be reverted in production without a data migration or manual state repair. | |
| RB4 | New code paths emit sufficient logs or metrics to diagnose a failure in production within an acceptable MTTD window. | Minimum: error-level log on every unexpected exception; key state transitions logged at info. |
| RB5 | External service calls have timeouts, retries with backoff, and fallback behavior defined. | Applies to HTTP, gRPC, database, message queue, and file system calls. |
