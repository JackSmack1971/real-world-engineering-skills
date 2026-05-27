# Severity Rubric

## Scoring Axes

Every finding is scored across five axes before a severity level is assigned.

| Axis | Low | Medium | High |
|------|-----|--------|------|
| **Exploitability** | Requires significant attacker capability, complex chain, rare precondition | Some conditions required; attacker needs partial access or knowledge | No special capability; reproducible by script kiddie or automated scanner |
| **Blast Radius** | Isolated to single non-critical function or component | Affects a bounded subsystem or moderate data volume | Full data exfil, privilege escalation to admin, service disruption, or supply chain compromise |
| **Attacker Effort** | Days to weeks; significant reverse engineering or brute force | Hours; tool-assisted exploitation | Minutes or seconds; off-the-shelf exploit or single request |
| **Detectability** | Leaves clear forensic trail; triggers existing monitoring | Detectable with enhanced logging; may be missed by default config | Leaves no log trace; bypasses existing monitoring; silent exfil possible |
| **Chainability** | Terminal — does not enable further exploitation | Enables lateral movement or privilege escalation to a second step | Required precondition for a CRITICAL path; enables full compromise chain |

---

## Severity Levels

### CRITICAL

**Definition**: Exploitable with low-to-medium effort, high blast radius, no authentication required (or authentication bypass is part of the finding), and low detectability in at least two of the five axes.

**Required evidence**:
- Complete exploit chain documented from entry point to impact
- Specific file and line reference
- Real precondition (not theoretical)

**Examples**:
- Unauthenticated remote code execution via unsanitized shell injection
- Secret key hardcoded in public repository with active service
- SQL injection allowing full database dump from unauthenticated endpoint
- Indirect prompt injection causing agent to exfiltrate secrets via tool call
- Deserialization of attacker-controlled data leading to arbitrary code execution

---

### HIGH

**Definition**: Exploitable with medium effort, significant impact, or is a required link in a CRITICAL exploit chain. Authentication or some precondition required, but precondition is plausibly achievable.

**Required evidence**:
- Traceable path from untrusted input to privileged action
- Identified control failure or missing control at a boundary
- Specific location

**Examples**:
- Authenticated SQL injection allowing privilege escalation
- SSRF enabling access to internal metadata service or non-public S3 bucket
- Insecure direct object reference allowing cross-tenant data access
- LLM output used to construct a shell command without validation (even with auth)
- Unpinned cryptographic library with active CVE in the transport path
- Path traversal in authenticated file-download endpoint

---

### MEDIUM

**Definition**: Exploitable under specific conditions, limited blast radius, or HIGH-severity class where the exploit chain cannot be fully confirmed with available information.

**Examples**:
- Reflected XSS in authenticated admin panel (limited blast radius)
- Missing `HttpOnly` / `Secure` cookie flags on session token
- Verbose error messages leaking stack traces or internal paths
- CORS misconfiguration allowing credentialed cross-origin reads from known subdomain
- Unvalidated redirect enabling phishing
- LLM output rendered as HTML without escaping (stored XSS potential)
- Dev-only `DEBUG=True` flag — MEDIUM if there is no evidence it reaches production, HIGH if it might

---

### LOW

**Definition**: Requires significant attacker effort, or exploitability is conditional on a very specific and unlikely precondition. No viable exploit chain to meaningful business impact.

**Examples**:
- Information disclosure of non-sensitive data (server version headers)
- Weak password policy without rate limiting (requires brute force over time)
- Missing security headers (`X-Frame-Options`, `X-Content-Type-Options`) with no viable phishing context
- Dependency with CVE in an unused code path
- Log injection with no log viewer that renders user input

---

### INFO

**Definition**: No exploitable security impact. Noted as a security hygiene improvement, not a vulnerability.

**Examples**:
- Overly permissive file permissions on non-sensitive config files
- Unused deprecated import of a historically vulnerable library (not reachable)
- Missing audit logging on a low-privilege operation
- Outdated dependency version with no known CVE

---

## Severity Adjustment Rules

### Upgrade triggers (raise one level)

- Finding is chainable: it enables or is required for a higher-severity exploit
- Control failure occurs at a public-facing or unauthenticated boundary
- Blast radius affects multiple tenants or all users (not just the authenticated principal)
- Existing monitoring is confirmed absent or bypassed by the exploit path

### Downgrade triggers (lower one level)

- Exploit requires an authenticated high-privilege account that is not commonly held
- Mitigating control exists at a downstream boundary that is independently validated
- Blast radius is confirmed isolated to non-sensitive data only
- Deployment environment evidence strongly suggests the vulnerable path is unreachable in production

### Override rule

If a finding produces a complete, mechanically simple exploit chain to CRITICAL-class impact, assign CRITICAL regardless of axis scores. Document the override rationale.

---

## Chainability Scoring

When two or more findings form a chain:

1. Identify the terminal finding (highest blast radius).
2. Identify all prerequisite findings (access, bypass, information disclosure).
3. Score the **chain** as a unit: the chain severity = terminal finding severity, adjusted upward if the chain requires no authentication at any step.
4. Each prerequisite finding that is required (not merely helpful) is upgraded one level from its standalone score.
5. Document the chain as its own entry in the Attack Graph section.
