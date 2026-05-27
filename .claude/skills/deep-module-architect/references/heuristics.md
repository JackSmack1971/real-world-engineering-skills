# Anti-Pattern Catalog and Extended Heuristics

Reference file for `deep-module-architect`. Load when running full architectural reviews, change amplification analysis across multiple files, or when the user requests the complete anti-pattern list.

---

## Table of Contents

1. Anti-Pattern Catalog
2. Change Amplification Root Causes
3. Flag Parameter Analysis
4. Interface Depth Scoring
5. Temporal Coupling Detection
6. Information Leakage Taxonomy

---

## 1. Anti-Pattern Catalog

### Pass-Through Method

**Definition**: Method A.foo() calls B.foo() with the same arguments and no additional logic, invariants, or transformation.

**Signal**: Identical signatures at two layers. Callers could call B.foo() directly.

**What it is not hiding**: Nothing. The caller knows B exists conceptually; the wrapper just renames the path.

**Fix**: Delete the wrapper. If A genuinely needs to intercept calls to B in the future, add it then with a reason.

---

### Shallow Wrapper Class

**Definition**: A class whose only job is to hold a reference to another class and forward calls, with no added invariants, policy, or hiding.

**Common forms**: `XxxAdapter`, `XxxProxy`, `XxxFacade` over a stable, non-volatile underlying API.

**Diagnosis**: If removing the wrapper and calling the underlying class directly would require no callers to change their mental model, the wrapper is shallow.

**Fix**: Eliminate the wrapper. If interface stability is the goal, the wrapper is only justified if the underlying API is genuinely volatile.

---

### Flag Parameter (Behavior Selector)

**Definition**: A boolean, enum, or string parameter passed to a function that selects fundamentally different code paths inside the implementation.

**Why it is shallow**: The caller is making a decision that belongs inside the module. The interface exposes internal structure.

**Diagnosis checklist**:
- Does the parameter appear in an `if`/`switch` that routes to completely different logic?
- Would removing the parameter require two separate, clearly named functions?
- Does the caller always pass a literal (`true`, `false`, `"json"`) rather than a computed value?

**Fix**: Split into two explicitly named functions. The names make the decision visible without exposing implementation structure. If both paths share setup code, extract the shared part privately.

```python
# Bad — flag parameter
def export(data, format: bool):  # True = JSON, False = CSV
    ...

# Good — pull decision to caller, hide implementation
def export_json(data): ...
def export_csv(data): ...
```

---

### Configuration Object Leaking Internals

**Definition**: A config struct or dict passed to a module contains keys that expose the module's internal structure (e.g., buffer sizes, retry counts, internal class names, thread counts).

**Why it matters**: The caller must know and set internal parameters, coupling them to implementation decisions.

**Fix**: Replace with semantic parameters (e.g., `throughput_class: Literal["low","high"]`) or set safe defaults internally and allow override only via well-named semantic options.

---

### Temporal Coupling in Interface

**Definition**: Callers must call methods in a specific sequence not enforced by the type system (e.g., must call `init()` before `run()`, must call `open()` before `read()`).

**Why it leaks complexity**: The caller must know and respect an invariant that lives outside the interface contract.

**Diagnosis**: Look for `init`, `setup`, `open`, `connect`, `begin`, `start` as separate public methods that gate later calls.

**Fix options**:
1. Constructor injection — move setup into `__init__`; object is valid immediately upon construction.
2. Builder pattern — enforce sequencing via type state (returned type only exposes next valid step).
3. Context manager — enforce lifecycle with `with` block.

---

### Duplicated Format / Schema Knowledge

**Definition**: Two or more modules contain hardcoded knowledge of the same data format (e.g., JSON field names, DB column names, CSV headers, wire protocol byte offsets).

**Why it amplifies change**: Changing the format requires editing every module that encodes it.

**Fix**: Create one canonical module that owns the format. All other modules depend on it. The format is never repeated.

---

### Inverted Abstraction (Caller Knows More Than Module)

**Definition**: The caller holds context that the module needs but was not designed to receive. Callers compensate by building logic the module should own.

**Common form**: A "util" or "helper" function called by callers to prepare data before passing it to the module, because the module doesn't handle that preparation itself.

**Fix**: Move the preparation logic into the module. The caller should supply raw intent, not pre-processed data.

---

### Abstraction Inversion

**Definition**: High-level operations are implemented by calling low-level operations that were themselves built on top of the high-level ones.

**Effect**: Unnecessary complexity, circular mental models, fragile sequencing.

**Fix**: Re-derive the high-level operations from the lowest available primitives.

---

## 2. Change Amplification Root Causes

When a single logical change touches ≥ 3 files, trace to one of these root causes:

| Root Cause | Diagnosis | Fix |
|-----------|-----------|-----|
| **Leaked representation** | Multiple modules know the internal data shape (field names, types, ordering). | Create one canonical data owner. Others depend on it. |
| **Leaked policy** | Multiple modules implement the same rule (validation, auth, formatting). | Extract the rule to one policy module. Others call it. |
| **Duplicated logic** | The same algorithm appears in multiple places with no canonical home. | Identify the canonical module and delete duplicates. |
| **Implicit protocol** | Callers must replicate a sequence or protocol the module should own. | Absorb the protocol into the module. Expose only the outcome. |

---

## 3. Flag Parameter Analysis

Severity classification for flag parameters:

| Severity | Condition | Action |
|----------|-----------|--------|
| **Critical** | Flag selects mutually exclusive code paths > 10 lines each | Split into two functions immediately |
| **High** | Flag is always a literal at call sites | Split; literal = caller knows the decision statically |
| **Medium** | Flag adds optional behavior that could default | Make it a keyword arg with a sensible default |
| **Low** | Flag controls minor formatting or verbosity | Acceptable if behavior paths share > 80% of implementation |

---

## 4. Interface Depth Scoring

Score any module on a 1–5 depth scale:

| Score | Condition | Interpretation |
|-------|-----------|---------------|
| **1 — Ceremonial** | 1:1 method-to-line ratio, no invariants added, caller still knows everything | Delete or collapse |
| **2 — Thin** | Adds minimal validation or type coercion only | Acceptable only if the boundary prevents a real error class |
| **3 — Functional** | Hides one stable implementation choice; interface is meaningfully simpler | Acceptable |
| **4 — Deep** | Interface hides multiple volatile decisions; callers are ignorant of N≥2 implementation facts | Good design |
| **5 — Strategic** | Stable interface over a highly volatile or complex implementation domain | Excellent; preserve at high cost |

A module scoring 1–2 is a candidate for collapse. A module scoring 4–5 should be protected from interface changes.

---

## 5. Temporal Coupling Detection

Look for these patterns in public interfaces:

```
# Pattern: lifecycle method pairs
obj.init()     # must be called first
obj.process()  # only valid after init
obj.close()    # must be called last

# Pattern: state-setting before action
parser.set_input(data)
parser.set_mode("strict")
result = parser.parse()    # valid only after set_* calls

# Pattern: output polling after trigger
runner.start(job)
# caller must poll or wait
status = runner.check()    # valid only after start
```

**Fix priority**: Constructor injection > context manager > builder > documented precondition (last resort).

---

## 6. Information Leakage Taxonomy

Types of leaked information, from most to least severe:

| Leak Type | Example | Severity |
|-----------|---------|----------|
| **Format leak** | Caller knows JSON field names or DB column layout | Critical — every schema change propagates |
| **Sequencing leak** | Caller must call methods in a specific order | High — bugs are silent and state-dependent |
| **Error shape leak** | Caller pattern-matches on internal exception types | High — internal refactors break external handling |
| **Resource leak** | Caller must manage lifecycle (open/close, acquire/release) | High — ownership is ambiguous |
| **Type leak** | Caller receives an internal implementation type | Medium — refactoring internal types breaks callers |
| **Naming leak** | Caller references internal class or module names as strings | Medium — renames ripple through callers |
| **Size/limit leak** | Caller knows buffer sizes, pagination limits, retry counts | Low-Medium — operational parameters couple caller to implementation |
