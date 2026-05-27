---
name: security-review
description: Performs adversarial security review of code changes, dependencies, secrets, injection paths, and OWASP LLM/Agentic compliance. Use when reviewing a PR diff, file path, or module before merge or deployment. Evaluates whether security invariants survive integration, deployment drift, runtime configuration, and adversarial sequencing. Produces severity-rated findings with complete exploit chains and remediation steps. Read-only reviewer role.
disable-model-invocation: true
allowed-tools: Read Glob Bash
argument-hint: <path-or-glob> [--scope deps|secrets|injection|llm|full]
---

## Expert Salience

Weight these signals before all other analysis:

1. **Trust boundary crossings** — data moving between principals, privilege levels, or trust zones
2. **Data provenance breaks** — points where input origin becomes unverifiable
3. **Control assumptions** — apparent mitigations that rely on upstream correctness
4. **Chainability** — LOW findings that compose into CRITICAL paths
5. **Attacker economics** — exploitability × blast radius ÷ (effort × detectability)

Suppress: style issues, formatting, theoretical paths with no viable attacker vector in the observed deployment context.

Core principle: **local correctness does not imply global security.** A control that holds in isolation but fails at a trust boundary is a finding. Security is an emergent property of the composed system.

---

## Mental Model: Trust Boundary Map

Before reading code, construct this map from the target:

```
[External Input] → [Validation/Parsing] → [Business Logic] → [Privileged Sinks]
   Trust Zone 0       Trust Zone 1           Trust Zone 2       Trust Zone 3
   (untrusted)        (sanitized?)            (internal)         (commands/DB/LLM/FS)
```

At each boundary crossing ask:
- What guarantee makes this data trustworthy at this point?
- Who controls that guarantee — can it be subverted?
- What fails if this assumption does not hold?

Hold every apparent control as an assumption to invalidate until the full call graph confirms it.

---

## Procedure

### Phase 1 — Scope Resolution

Parse `$ARGUMENTS`. Extract target path and optional `--scope` flag.
Default when no flag: `full` (all phases).

```bash
# Establish repo context
git diff --stat HEAD 2>/dev/null | head -30 || true
git log --oneline -5 2>/dev/null || true
```

Read target files via `Read`. Enumerate with `Glob`. Do not write anything.

---

### Phase 2 — Attack Surface Enumeration

Map all entry points:
- HTTP / gRPC / WebSocket endpoint handlers
- CLI argument parsers
- File format parsers: YAML, JSON, XML, TOML, Markdown, CSV
- Environment variable readers
- LLM prompt construction sites (system prompt builders, context injection, RAG retrievers)
- Agent tool-call dispatchers and result handlers
- Message queue / event stream consumers
- IPC and inter-service boundaries

For each entry point trace: `[source] → [transforms] → [sink]`

Flag: sinks that are shell commands, file writes, SQL queries, LLM prompts, external HTTP calls, or deserialization.

---

### Phase 3 — Secret Exposure Scan

```bash
TARGET="${1:-.}"
grep -rn \
  -e "api[_-]key\s*=\s*['\"][^'\"]\+" \
  -e "secret\s*=\s*['\"][^'\"]\+" \
  -e "password\s*=\s*['\"][^'\"]\+" \
  -e "token\s*=\s*['\"][^'\"]\+" \
  -e "-----BEGIN" \
  -e "Authorization: Bearer" \
  --include="*.py" --include="*.js" --include="*.ts" \
  --include="*.go" --include="*.rb" --include="*.env" \
  --include="*.yaml" --include="*.yml" --include="*.json" \
  --include="*.toml" --include="*.conf" --include="*.cfg" \
  "$TARGET" 2>/dev/null || true
```

Also check:
- `.env` files present in the repo tree
- Secrets embedded in test fixtures or seed data
- Hardcoded URLs with credentials in query strings or basic-auth format
- Log statements (`print`, `logger.*`, `console.log`) emitting sensitive fields

---

### Phase 4 — Dependency Risk

Read manifest files: `package.json`, `requirements*.txt`, `go.mod`, `Cargo.toml`, `pyproject.toml`, `pom.xml`, `build.gradle`.

Evaluate:
- Unpinned versions (`>=`, `^`, `~`, `*`) on auth, crypto, or HTTP libraries
- Packages with documented CVE history in critical paths — cite real CVEs only, never fabricate
- Abandoned maintainership: last publish date, contributor count, open issues ratio
- Suspicious recent activity: new maintainer, version bump with no changelog, renamed package
- Dev dependencies that may leak into production bundles (check build config)

---

### Phase 5 — Injection Path Traversal

For each untrusted-input → privileged-sink path from Phase 2, trace the complete transform chain.

At each transform step ask:
- Does this neutralize the injection class for **all** inputs in the full type domain?
- Is the transform applied before or after routing/branching logic?
- Can the attacker influence which transform is selected?

**Flag patterns:**

| Class | Indicators |
|---|---|
| SQL | String concatenation or f-string into query; ORM `raw()`/`execute()` with user data |
| Shell | `subprocess(shell=True)`, `os.system`, `exec()`, unquoted `$VAR` in scripts |
| Path traversal | `os.path.join` with user segments; `../` not stripped before FS access |
| Template injection | User data into Jinja2 / Handlebars / Pebble without sandboxing |
| SSRF | User-controlled URL passed to HTTP client without strict allowlist |
| Deserialization | `pickle.loads`, `yaml.load` (not `safe_load`), Java `ObjectInputStream`, `eval(JSON)` |
| Log injection | Newline / CRLF in user data written directly to log streams |
| XSS | Unescaped user content rendered in HTML, `innerHTML`, `dangerouslySetInnerHTML` |

---

### Phase 6 — LLM/Agentic Compliance

Load `references/owasp-llm-agentic.md`. Evaluate each applicable item against the target.

Priority evaluation order:
1. **LLM01** — Prompt injection: direct (user input in prompt) and indirect (retrieved content, tool output, file content injected into context)
2. **LLM02** — Insecure output handling: LLM output trusted as structured data without schema validation or sanitization
3. **LLM06** — Sensitive information disclosure: PII, credentials, or internal system data reachable via crafted prompts or RAG poisoning
4. **LLM08** — Excessive agency: tools granted without need-to-use scoping; tool permissions not proportional to declared task
5. **LLM09** — Overreliance: LLM output used in security-critical decisions (access control, financial ops) without human gate or deterministic validation
6. **Agentic — Tool authorization**: are tool invocations gated by intent verification, not just availability?
7. **Agentic — Prompt exfiltration**: can an adversarial document route tool output to an attacker-controlled endpoint via chained tool calls?
8. **Agentic — Confused deputy**: can a low-privilege principal cause a high-privilege agent to act on its behalf by manipulating prompt context?

---

### Phase 7 — Deployment Drift and Runtime Configuration

Check for:
- Security controls that may be disabled in dev/staging environments: `DEBUG=True`, `CORS_ORIGINS=*`, `VERIFY_SSL=False`, `AUTH_REQUIRED=False`
- Feature flags that toggle security behavior without separate audit trail
- Secrets baked into build artifacts vs. injected at runtime via secrets manager
- Default-insecure library configuration (e.g., permissive CORS, missing `HttpOnly`/`Secure` cookie flags, disabled CSRF protection)
- Divergence between documented deployment requirements and observed code defaults

---

### Phase 8 — Adversarial Sequencing

For each HIGH+ finding, attempt chaining with other findings:
- Can an attacker use Finding A to satisfy the precondition for Finding B?
- Does the combined chain elevate severity?
- What is the minimum-step exploit path from zero privilege to maximum business impact?

Document as an attack graph in the output summary.

---

## Output Format

```
## Security Review: <target>
Scope: <scope applied> | Role: adversarial read-only
Trust boundary map: <brief map — 3–5 nodes>

---

### FINDING-NNN | <SEVERITY> | <Category>

**Location**: `path/to/file.py:42`
**Exploit chain**: [Entry point] → [Transform bypass] → [Sink] → [Impact]
**Preconditions**: <specific attacker-controlled state required>
**Business blast radius**: <data exfil / privilege escalation / service disruption / supply chain>
**Attacker economics**: effort=<low|med|high> | detectability=<low|med|high> | chainable=<yes/no>
**Severity rationale**: <why this level, not one above or below>
**Remediation**:
  1. <Specific fix referencing the actual code location>
  2. <Defense-in-depth layer>
  3. <Detection or monitoring recommendation>
**Assumptions invalidated**: <which assumed control does not hold here>

---

## Summary Table

| ID | Severity | Category | Chainable | Blast Radius |
|----|----------|----------|-----------|--------------|

## Attack Graph

<Narrative of the highest-priority multi-finding exploit chain>

## Invariants at Risk

<Security invariants that do not survive the composed system as reviewed>
```

Load `references/severity-rubric.md` for full scoring criteria.
Load `references/attack-patterns.md` for injection class bypass patterns and supply chain indicators.

---

## Decision Heuristics

- **Boundary invariants override isolated correctness.** A locally correct control that fails at any trust boundary crossing in the call graph is a finding.
- **Chainability multiplier.** A LOW finding that is a required precondition for a CRITICAL chain is scored HIGH.
- **Uncertainty defaults to absent control.** If a control cannot be confirmed across all runtime configurations, treat it as absent and document the assumption.
- **Exploit chain required for HIGH+.** Do not assign HIGH or CRITICAL without a written complete exploit chain. Downgrade to MEDIUM if the chain cannot be completed with available information.
- **Attacker economics dominate scoring.** A mechanically simple path with high blast radius scores up regardless of documented control presence.

---

## Commitment Thresholds

Do not assign CRITICAL without:
1. A complete attacker-controlled exploit chain from entry point to measurable business impact
2. A specific, real precondition — not "if the attacker has network access in theory"
3. A file path and line reference

Do not assign HIGH without:
1. A traceable path from untrusted input to privileged action
2. An identified control failure or missing control at a boundary

---

## Anti-Patterns

- Do not produce checklist completion reports. Produce exploit chains.
- Do not assign severity by CVSS score alone. Score by attacker economics + blast radius + chainability.
- Do not mark a control "mitigated" because it exists locally. Verify it holds at every boundary crossing.
- Do not fabricate CVE IDs. Reference real, known CVEs only.
- Do not report findings without remediation steps specific to the observed code.
- Do not suppress a finding because a comment claims it is safe. Validate the claim.

---

## Uncertainty Handling

State every unresolved assumption explicitly in the finding:

> **Assumption**: Deployed with default configuration. If `VARIABLE=value` is overridden in production, this finding does not apply.

Tag assumption-dependent findings: `[ASSUMPTION-DEPENDENT]`

If the deployment environment is entirely unknown, scope findings to observable code only and open a separate `## Unresolvable Assumptions` section listing environment gaps that materially affect the risk assessment.
