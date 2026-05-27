# Aggregate Discipline: Sizing Rules and Invariant Checklist

Reference for `ddd-policy`. Load this file when the task involves aggregate design, invariant boundary decisions, transaction scope, or object-graph composition questions.

---

## Core Principle

An aggregate is a **consistency boundary**, not a storage unit or a graph traversal shortcut. Its shape is determined entirely by which invariants must hold atomically.

---

## Invariant Identification Checklist

Before sizing any aggregate, answer these questions. Every "yes" is evidence for including the object in the aggregate. Every "no" is evidence for referencing by identity instead.

| Question | Include in aggregate | Reference by identity |
|---|---|---|
| Does this object participate in an invariant that must hold atomically? | ✅ | |
| Can the invariant be checked without loading this object? | | ✅ |
| Does this object have an independent lifecycle (can it exist without the root)? | | ✅ |
| Is this object modified by a workflow other than the root's primary workflow? | | ✅ |
| Can a one-second inconsistency window between this object and the root be tolerated? | | ✅ |
| Would loading this object require > 1 additional query or join? | | ✅ (check invariant scope) |
| Is this object the target of a query that the root is not the subject of? | | ✅ |

**Rule of thumb:** If you cannot complete the sentence "The aggregate root enforces the invariant that ___________", the aggregate boundary is wrong.

---

## Sizing Rules

### Rule 1: One invariant statement per aggregate
State the invariant in one sentence. If you need "and" or multiple clauses, you likely have more than one aggregate.

**Valid:** "An Order's total must equal the sum of its confirmed OrderLine prices."
**Invalid:** "An Order tracks its lines AND manages customer credit AND coordinates with inventory."

### Rule 2: Transaction boundary = aggregate boundary
One database transaction should modify at most one aggregate root. If a use case requires atomicity across two aggregates, it belongs in a saga, not a transaction.

### Rule 3: Reference child aggregates by identity
Objects outside the consistency boundary are referenced by their identity (a value object wrapping a UUID or domain identifier), never by direct object reference.

```
// Correct
class Order {
  private CustomerId customerId;  // identity reference, not Customer object
  private List<OrderLine> lines;  // inside the aggregate boundary
}

// Incorrect
class Order {
  private Customer customer;  // direct reference to another aggregate
}
```

### Rule 4: Small aggregates by default
Begin with the smallest possible aggregate that enforces one invariant. Enlarge only when an invariant cannot be expressed without including additional objects. Splitting a live aggregate is a migration event; starting small is cheap.

### Rule 5: Eventual consistency between aggregates
Side effects on other aggregates are triggered by domain events, not by direct method calls inside the same transaction.

```
// Correct
order.confirm();  // raises OrderConfirmed event
// Handler: inventory.reserve(event.productId, event.quantity)  — separate transaction

// Incorrect
order.confirm(inventory);  // cross-aggregate coordination inside one transaction
```

---

## Aggregate Root Responsibilities

The root is responsible for:
1. Enforcing all invariants for the cluster
2. Being the only entry point for state changes (no external mutation of children)
3. Raising domain events that represent meaningful state transitions
4. Controlling the lifecycle: creation, modification, and deletion of all child objects

The root is NOT responsible for:
- Cross-aggregate queries (use read models or query services)
- Orchestrating workflows across multiple aggregates (use application services or sagas)
- Reporting or analytics (use projections from domain events)

---

## Domain Events from Aggregates

Domain events record **that something happened** within the aggregate boundary, not instructions to other systems.

**Event naming:** Past tense, context-prefixed, aggregate-specific.
- `orders.OrderConfirmed.v1`
- `billing.InvoiceIssued.v1`
- `inventory.StockReserved.v1`

**Event envelope (minimum):**
```json
{
  "eventType": "orders.OrderConfirmed.v1",
  "aggregateId": "<order-id>",
  "aggregateVersion": 7,
  "occurredAt": "<iso-timestamp>",
  "payload": { ... }
}
```

Never embed another aggregate's state in the payload. Reference by identity only.

---

## Anti-Patterns: Aggregate Mistakes

### God Aggregate
**Symptoms:** Aggregate has > 10 child entities; loading it requires multiple joins; multiple teams need to modify it; it is called "Entity" or named after a database table.
**Fix:** Identify independent lifecycles; extract sub-aggregates; link by identity.

### Aggregate as DTO
**Symptoms:** Aggregate has only getters and setters; invariants are checked in service classes.
**Fix:** Move invariant logic into the aggregate root; make state-changing methods express business intent (`order.confirm()`, not `order.setStatus("CONFIRMED")`).

### Lazy-Load Excuse
**Symptoms:** Deep object graph justified by "we'll use lazy loading."
**Fix:** Lazy loading hides aggregate sizing problems; do not use it as a substitute for proper boundary design.

### Cross-Aggregate Method Call
**Symptoms:** Aggregate root accepts another aggregate as a method parameter and calls methods on it.
**Fix:** Pass only identity references; emit a domain event; let a saga or application service coordinate.

---

## Lifecycle State Machine Template

Every aggregate root should have an explicit lifecycle. Document it before coding.

```
[Created] → [Active] → [Suspended] → [Active]
                    ↘ [Cancelled]
                    ↘ [Archived]
```

Invariant transitions must be validated at the root. Illegal transitions raise a domain exception, not a validation error from an application service.

---

## Transaction Scope Decision Matrix

| Scenario | Correct approach |
|---|---|
| Single aggregate, single context | One transaction |
| Two aggregates, same context, causally related | Domain event + async handler (separate transactions) |
| Two aggregates, different contexts | Domain event + ACL + async handler |
| Rollback required across aggregates | Saga with compensating actions |
| Read across multiple aggregates | Read model / projection; never load aggregates for query |
