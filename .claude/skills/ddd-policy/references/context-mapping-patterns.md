# Context-Mapping Pattern Catalog

Reference for `ddd-policy`. Load this file when the task involves cross-context integration design, relationship classification, or partnership governance.

---

## Pattern Quick-Select

| Situation | Pattern |
|---|---|
| Two teams co-evolve a shared subset of the model | Shared Kernel |
| Upstream team sets the contract; downstream adapts | Customer–Supplier |
| Downstream team accepts upstream model without translation | Conformist |
| Downstream team translates upstream model at the boundary | Anti-Corruption Layer |
| Context publishes a formal, stable API for multiple consumers | Open Host Service + Published Language |
| Contexts have no integration worth maintaining | Separate Ways |
| Two teams with equal negotiating power co-develop together | Partnership |
| Legacy or unmanageable context leaking into new design | Big Ball of Mud |

---

## Pattern Details

### Shared Kernel
**Applicability:** Two BCs with high semantic overlap and a single team (or tightly coordinated teams) that can govern changes jointly.

**Mechanics:**
- Define the shared subset explicitly: shared value objects, shared events, shared identifiers
- Any change to the kernel requires both teams to agree and both test suites to pass
- The kernel is NOT a general-purpose library — it must be the minimum semantic overlap required

**Risks:**
- Grows into a Universal Model if governance weakens
- High coordination cost; prefer ACL if teams are independent

**When to reject:** Teams have different release cadences, different ownership, or different domain vocabularies. Use ACL instead.

---

### Customer–Supplier
**Applicability:** Upstream (Supplier) controls the model; downstream (Customer) has some negotiating power to request changes.

**Mechanics:**
- Customer defines acceptance tests that the Supplier must pass
- Supplier publishes a contract; Customer adapts to it
- Changes are negotiated, not unilateral

**Risks:**
- Devolves into Conformist if Customer loses influence
- Supplier may break Customer without realizing it if acceptance tests are weak

---

### Conformist
**Applicability:** Downstream has no negotiating power over upstream and the upstream model is stable enough to inherit directly.

**Mechanics:**
- Downstream uses upstream model objects directly, with no translation layer
- Upstream changes propagate automatically to downstream

**Use only when:**
- Upstream model is stable (low churn)
- Upstream vocabulary maps cleanly to downstream needs
- The cost of an ACL exceeds the cost of semantic coupling

**Warning:** Conformist is the highest-risk pattern. It creates hard semantic coupling. Prefer ACL for any unstable or poorly governed upstream.

---

### Anti-Corruption Layer (ACL)
**Applicability:** Any integration where the upstream model must not contaminate the downstream BC's domain logic.

**Mechanics:**
- ACL sits at the downstream boundary
- Translates upstream concepts into downstream ubiquitous language
- Upstream changes are absorbed at the ACL; the downstream model is protected
- Usually implemented as a set of translators / adapters / facades

**Structure:**
```
[Upstream Context] → [ACL: Translator] → [Downstream Context]
```

**Always use when:**
- Upstream model is unstable or poorly governed
- Upstream vocabulary conflicts with downstream vocabulary
- Integrating with a legacy system or third-party API

**Never skip the ACL to save time.** Skipping creates a direct semantic dependency that propagates upstream churn into core domain logic.

---

### Open Host Service + Published Language
**Applicability:** A context that serves multiple downstream consumers and wants to decouple from their individual needs.

**Mechanics:**
- Context publishes a formal, versioned API (Open Host Service)
- The API uses a Published Language: a shared schema or protocol that consumers can depend on
- Consumers bind to the Published Language, not internal model objects

**Published Language attributes:**
- Versioned (e.g., `v1`, `v2`)
- Stable: breaking changes require a new version
- Self-describing: schema contracts, event envelopes, or IDL definitions
- Prefixed with context name: `billing.InvoiceIssued.v1`

**When to use:** Any context that has > 1 downstream consumer. Do not publish internal aggregates directly — always translate to Published Language.

---

### Separate Ways
**Applicability:** Two contexts have minimal interaction; the cost of integration exceeds the value.

**Mechanics:**
- Contexts are explicitly declared independent
- If overlapping functionality is needed, it is duplicated locally rather than integrated
- No shared model, no integration point

**Use when:** Integration is technically possible but the semantic overlap is trivial, teams operate in completely different domains, or the cost of maintaining the translation layer is not justified.

---

### Partnership
**Applicability:** Two teams with equal negotiating power must succeed or fail together on a shared initiative.

**Mechanics:**
- Joint planning of the shared interface
- Coordinated releases
- Shared CI/CD pipeline for the integration point
- Either team can block a release that breaks the interface

**Risks:**
- High coordination overhead
- Time-limited: reassess after the shared initiative concludes
- Tends to produce a Shared Kernel if the partnership persists; govern accordingly

---

### Big Ball of Mud
**Applicability:** Legacy context with no clear boundaries, mixed languages, and inconsistent semantics.

**Mechanics:**
- Acknowledge the BBoM explicitly in the context map
- Wrap it entirely with an ACL on every outbound integration
- Do not attempt to refactor from inside a new BC; translate at the boundary

**Warning:** Never let a BBoM's model leak directly into a new BC. The ACL is non-negotiable here.

---

## Context Map Drawing Rules

1. Name every context (noun phrase, team-owned)
2. Draw every integration as a directed arrow: upstream → downstream
3. Label every arrow with its pattern
4. Mark relationship properties: `[PL]` Published Language, `[ACL]` Anti-Corruption Layer, `[SK]` Shared Kernel
5. Mark edge confidence: `CONFIRMED`, `SUSPECTED`, `CONFLICTED`
6. Review the map when: a new integration is added, a team changes ownership, or a shared model grows unexpectedly

---

## Integration Mechanics Decision Tree

```
Is there semantic overlap between contexts?
├── No → Separate Ways
└── Yes
    ├── Do both teams have equal negotiating power and a shared goal?
    │   └── Yes → Partnership (time-limited) or Shared Kernel (governed)
    └── No
        ├── Is the upstream model stable and vocabulary-compatible with downstream?
        │   ├── Yes, and downstream has negotiating power → Customer–Supplier
        │   ├── Yes, and downstream has no negotiating power → Conformist (evaluate ACL cost)
        │   └── No (unstable, incompatible, or legacy) → ACL (mandatory)
        └── Does the context serve multiple consumers?
            └── Yes → Open Host Service + Published Language
```
