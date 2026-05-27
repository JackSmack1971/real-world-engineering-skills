---
name: ddd-policy
description: "Applies Practical Domain-Driven Design engineering policy. Triggers on: bounded context design, aggregate modeling, context mapping, ubiquitous language review, domain events, anti-corruption layers, DDD architecture review, shared model analysis, domain isolation decisions, invariant boundary questions, integration pattern selection, strategic DDD planning. Enforces bounded-context autonomy, semantic isolation, aggregate root discipline, and active detection of the Universal Model Fallacy. Does NOT trigger on generic OOP design, microservice sizing without DDD framing, database schema scaffolding, or CRUD endpoint generation unless DDD concepts are explicitly named."
---

## Purpose

Enforce Practical DDD policy by reasoning from **strategic boundaries before tactical patterns**. Weight local semantic ownership and immediate invariant protection above enterprise reuse, object-graph completeness, or synchronous transaction convenience. Cross-context coordination is correct only when it is explicit, translated, and owned.

---

## Expert Salience

| Signal | Weight | Action |
|---|---|---|
| Word used differently across teams | HIGH | Suspect shared model; probe for separate BCs |
| Aggregate mutation from multiple workflows | HIGH | Check for missing BC split or root violation |
| "Universal" or "enterprise" domain model praised for reuse | HIGH | Activate Universal Model Fallacy check |
| Cross-context integration via direct object reference | HIGH | Replace with identity reference + ACL |
| Shared mutable table between two contexts | HIGH | Assign ownership; expose via event or API |
| Aggregate that crosses a service or transaction boundary | HIGH | Decompose or accept eventual consistency |
| Team refers to "the model" without qualification | MEDIUM | Probe ownership and lifecycle before continuing |
| Large aggregate with deep object graph | MEDIUM | Check invariant locality; split candidates |
| Synchronous cross-context call on the critical path | MEDIUM | Evaluate domain event + saga alternative |

**Ignore until the context map is stable:** technology choices, ORM convenience, framework idioms, and "best practice" reuse that crosses context lines.

---

## Mental Models

### 1. Bounded Context
A BC is a named semantic boundary within which one team **owns, defines, and enforces** a ubiquitous language. A word that means different things to different teams is not a ubiquitous language — it is a liability. The UL is local by definition.

Probe questions:
- Who owns the definition of this term?
- Can its meaning change independently of other contexts?
- Does the full lifecycle of this concept live entirely here?

### 2. Aggregate Root Discipline
An aggregate root is the **only entry point** for enforcing invariants over a cluster of objects. Size it by invariant scope, not by object-graph completeness or storage convenience.

Probe questions:
- What invariants must hold atomically under this root?
- What changes together, always, and only here?
- What can tolerate eventual consistency with a separate aggregate?

### 3. Context Map
The context map is the explicit record of **how contexts integrate**: translation mechanics, ownership direction, conformism, partnership terms, event contracts. No integration is invisible. Every cross-context dependency is named, typed, and owned.

→ Full pattern catalog: `references/context-mapping-patterns.md`

---

## Thinking Rules

1. **Semantic suspicion first.** Shared vocabulary is suspicious until ownership, meaning, invariants, lifecycle, and integration mechanics are proven local to a named context.

2. **Local before global.** Local semantic ownership and immediate invariant protection outweigh enterprise reuse, large object graphs, and synchronous transaction convenience.

3. **Translation is not failure.** ACLs and Published Languages are the correct cross-context answer. "Duplication" between models in different BCs is healthy isolation, not waste.

4. **Domain events are the coordination primitive.** Cross-context side effects belong in domain events, not synchronous service calls, shared transactions, or god-objects.

5. **Name the model, then the context.** A model that cannot be named and bounded is an implementation detail wearing domain clothing.

6. **Aggregates protect invariants, not data.** If the sole reason two objects share a root is co-location or retrieval convenience, the aggregate is wrong.

7. **Default smaller on boundary disputes.** Enlarging is cheaper than splitting; splitting a live aggregate is a migration event.

---

## Decision Heuristics

**On aggregate sizing:**
- Cannot state the invariant the aggregate enforces → split it
- Aggregate spans a service or transaction boundary → reduce to identity reference + eventual consistency
- Loading it requires > 3 joins or nested eager loads → check whether child entities are independent aggregates
- Invariant can tolerate a one-second window of inconsistency → it belongs in a separate aggregate with eventual consistency

**On context boundaries:**
- Same word, two teams, different meanings → mandatory BC split
- Downstream context modifies upstream model in place → immediate BC split + ACL
- Model is shared and "owned by everyone" → treat as ownerless; assign or split
- Two teams co-evolve a shared kernel → formalize with explicit shared kernel contract and governance

**On integration patterns:**
- Upstream model is stable and well-governed → Conformist may be acceptable; evaluate ACL cost
- Upstream model is unstable or poorly governed → ACL is mandatory; never Conformist on a volatile upstream
- Contexts need to exchange data at runtime → domain event + subscription; not shared DB, not RPC on critical paths

**On transactions:**
- Use case requires atomicity across aggregates → domain event + saga; never distributed transaction
- Synchronous cross-context call fails frequently → replace with async event + compensating action

→ Aggregate sizing rules: `references/aggregate-discipline.md`

---

## Commitment Thresholds

Do not commit to a **context boundary** until:
1. The ubiquitous language is named and its owning team is identified
2. At least one invariant local to the context is articulated
3. Integration mechanics with at least one neighboring context are named (even if undetailed)

Do not commit to an **aggregate boundary** until:
1. The atomic invariant is stated explicitly in one sentence
2. The full lifecycle (create / modify / archive / delete) is owned entirely within this context
3. The transaction scope does not cross a context boundary

If any threshold is unmet: produce a **context map draft**, mark ambiguous edges as `SUSPECTED` / `CONFIRMED` / `CONFLICTED`, and surface the gaps before any tactical modeling proceeds.

---

## Anti-Patterns

### Universal Model Fallacy — PRIMARY PATTERN

**Detection:** A "ubiquitous language" is described as enterprise-wide; shared entities are praised for avoiding duplication across teams or services; a single "Customer", "Product", or "Order" object is handed to every workflow.

**Correction:**
1. Enumerate every team or workflow using the shared model
2. Probe for word overloading: does "Order" mean the same thing in Fulfillment, Billing, and Customer Service?
3. Split at every semantic divergence: separate BCs, separate models, explicit translation
4. Replace shared mutable objects with identity references across boundaries; translate at ACL seams

→ Full detection checklist: `references/universal-model-fallacy.md`

### Oversized Aggregate
**Detection:** Aggregate root contains entities with independent lifecycles; loading it joins > 3 tables; multiple workflows modify different parts of it.
**Correction:** Decompose by invariant scope; reference children by identity; accept eventual consistency where the invariant permits.

### Anemic Domain Model
**Detection:** Domain objects are data bags; all business logic lives in Application Services or "Manager" classes.
**Correction:** Move invariant enforcement into the aggregate root; push validation and state-transition rules into value objects and entities; eliminate service classes that are really just procedure runners.

### Shared Database Integration
**Detection:** Two contexts read or write the same table or schema. Often defended as "it's just a view" or "read-only".
**Correction:** Assign schema ownership; expose cross-context data via domain events or read models; never share a mutable schema across BC boundaries.

### Context-Free Domain Events
**Detection:** Events published without a named originating context or owning aggregate root; no version or schema contract.
**Correction:** Prefix event names with context (`billing.InvoiceIssued`); include aggregate identity, version, and timestamp; publish under a formal schema contract (Published Language).

### Synchronous Cross-Context Transaction
**Detection:** A use case calls two services in sequence and rolls back both on failure; XA transactions or two-phase commit across services.
**Correction:** Decompose into a saga; publish domain events; accept temporary inconsistency with compensating actions.

---

## Uncertainty Handling

- Context boundary unclear → produce a candidate context map; mark edges as `SUSPECTED`; do not proceed to aggregate design
- Aggregate boundary disputed → default smaller; revisit when invariants are observed at runtime
- Integration mechanic unknown → assume ACL until the upstream model is proven stable and well-governed
- Team refers to "the domain model" without qualification → treat as Universal Model Fallacy risk; probe ownership before any tactical advice

---

## Worked Example

**Input:** "We have a shared `Customer` entity used by Sales, Billing, and Support. Should we model it as a single aggregate in a shared service?"

**Steps:**
1. Apply semantic suspicion — probe meanings:
   - Sales: prospect + contract negotiation lifecycle
   - Billing: payment account + invoice history + payment method
   - Support: interaction history + entitlements + SLA tier
2. Detect word overloading → three distinct meanings → Universal Model Fallacy
3. Identify three BCs: `sales-context`, `billing-context`, `support-context`
4. Define per-context models: `SalesProspect` / `BillingAccount` / `SupportProfile`
5. Link by shared external identity (customer ID as a value object in each context)
6. Coordination: Sales publishes `CustomerContractSigned`; Billing subscribes via ACL, creates `BillingAccount`; Support subscribes independently, creates `SupportProfile`
7. Result: no shared mutable aggregate; each context owns its invariants; cross-context coupling is explicit, event-driven, and translated

---

## References

- Context-mapping pattern catalog: `references/context-mapping-patterns.md`
- Aggregate sizing rules and invariant checklist: `references/aggregate-discipline.md`
- Universal Model Fallacy detection and correction playbook: `references/universal-model-fallacy.md`
