# Universal Model Fallacy: Detection and Correction Playbook

Reference for `ddd-policy`. Load this file when a shared model is suspected, when "enterprise-wide ubiquitous language" is claimed, or when the Universal Model Fallacy check is activated from the main skill.

---

## Definition

The Universal Model Fallacy is the error of mistaking a **local ubiquitous language** for an **enterprise-wide universal language**. The result is:

- Semantic coupling across bounded contexts
- A shared model that no single team fully owns
- Vocabulary inflation: a single word carries incompatible meanings
- Oversized aggregates that must satisfy every context's invariants
- DDD theater: bounded contexts named but not enforced; shared objects passed everywhere

The fallacy is seductive because it looks like discipline ("one model for everything") but is the opposite: it collapses the semantic boundaries that make DDD work.

---

## Detection Checklist

Work through this checklist whenever a shared model is presented. A positive on any HIGH item is sufficient to trigger a BC split recommendation.

### RED (Immediate BC split required)

- [ ] The same entity name (e.g., `Customer`, `Order`, `Product`) is used by > 1 team and at least one team uses it differently
- [ ] A shared entity is mutated by multiple workflows in different departments or services
- [ ] The shared model is described as "the source of truth for the whole company"
- [ ] Teams refer to "the domain model" (singular, unqualified) with no owning team named
- [ ] Adding a field to a shared entity requires sign-off from > 1 team
- [ ] A shared model is stored in a shared database schema accessed by > 1 service
- [ ] The shared model's lifecycle spans multiple business workflows (e.g., a `Customer` is created in Sales, modified in Billing, and queried in Support)

### AMBER (Probe further; likely BC split)

- [ ] The same word is used across contexts but with slightly different meanings ("same but different")
- [ ] A model is used as-is across contexts "for now" with a plan to split "later"
- [ ] The shared model has grown steadily over 6+ months without a clear ownership review
- [ ] Developers in different teams have different mental models of the same entity
- [ ] Tests in one context break when a different context changes the shared model

### GREEN (Shared model may be legitimate — verify)

- [ ] The shared concept is a pure value object (no lifecycle, no mutation, no identity)
- [ ] The shared concept is an infrastructure primitive (currency codes, country codes, standard enumerations)
- [ ] A formal Shared Kernel is in place with explicit governance, bounded scope, and joint test ownership

---

## Probe Questions

Ask these questions in sequence when evaluating a shared model. Stop when you have enough to make a recommendation.

1. "Who owns the definition of [entity name]? Which team decides what it means?"
2. "Does [entity name] mean the same thing in [Context A] and [Context B]? Walk me through what data each context reads and writes."
3. "If [Context A] needed to add a field to [entity name] that [Context B] doesn't care about, who approves that change?"
4. "What happens to [entity name] when a customer churns? Who initiates that lifecycle change?"
5. "How many services or teams query [entity name] in a given week? Do all of them need the same fields?"
6. "Has this model grown in the last year? Who requested the additions?"

---

## Common Manifestations

### The Mega-Customer
A `Customer` object owned by no one that contains Sales prospect data, Billing payment data, Support interaction data, and Identity authentication data. Every service reads it; multiple services write it.

**Correct split:**
- `SalesProspect` (Sales BC)
- `BillingAccount` (Billing BC)
- `SupportProfile` (Support BC)
- `UserCredential` (Identity BC)
- Linked by a shared `CustomerId` value object (external identity)

### The Omnibus Order
An `Order` that means a shopping cart in the Commerce context, a fulfillment task in the Warehouse context, an invoice request in the Billing context, and a shipment record in the Logistics context.

**Correct split:**
- `Cart` / `PlacedOrder` (Commerce BC)
- `FulfillmentTask` (Warehouse BC)
- `Invoice` (Billing BC)
- `Shipment` (Logistics BC)
- Coordination via domain events: `OrderPlaced`, `FulfillmentStarted`, `InvoiceIssued`, `ShipmentDispatched`

### The Product Catalog Monolith
A `Product` object that contains pricing, inventory count, marketing copy, SEO metadata, and tax classification — because "it's all about the product."

**Correct split:**
- `ProductListing` with marketing copy and SEO (Catalog BC)
- `PricingRule` (Pricing BC)
- `StockKeepingUnit` with inventory count (Inventory BC)
- `TaxClassification` (Tax BC)
- Linked by shared `ProductId`

---

## Correction Playbook

### Step 1: Enumerate consumers
List every team, service, or workflow that reads or writes the shared model.

### Step 2: Map vocabulary per consumer
For each consumer, write one sentence describing what the entity means to them and which fields they actually use.

### Step 3: Identify semantic divergence points
Mark every field or behavior that has a different meaning in different contexts. Each divergence point is a candidate BC boundary.

### Step 4: Assign ownership
Each BC gets one owning team. The BC's model is that team's responsibility. Other BCs do not modify it.

### Step 5: Define identity references
Replace direct object references across BCs with a shared identity value object (e.g., `CustomerId`, `ProductId`). Each BC maintains its own model, linked by identity.

### Step 6: Design the integration
For each cross-BC interaction, select a context-mapping pattern (ACL, Published Language, Customer–Supplier, etc.). Document it in the context map.

### Step 7: Migrate incrementally
- Start with read separation: each BC reads from its own read model
- Then separate writes: each BC writes to its own schema
- Finally, publish domain events at state transitions; remove direct cross-BC queries

---

## Migration Risk Classification

| Migration step | Risk level | Mitigation |
|---|---|---|
| Separate read models | Low | Add projections; leave shared DB temporarily |
| Separate write paths | Medium | Dual-write period with reconciliation check |
| Remove shared schema | High | Full event-sourced migration; requires cutover plan |
| Split a live aggregate | High | Saga + compensating actions; feature-flagged rollout |

---

## Fallacy Severity Scoring

Score the shared model against the RED checklist above. Use this table to communicate urgency.

| RED items triggered | Severity | Recommendation |
|---|---|---|
| 0 | None | No action required; verify GREEN items |
| 1–2 | Moderate | Initiate context map review; plan incremental split |
| 3–4 | High | Immediate BC split design required; freeze shared model growth |
| 5+ | Critical | Stop adding features to the shared model; begin emergency migration planning |
