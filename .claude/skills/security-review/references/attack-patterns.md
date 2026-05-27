# Attack Pattern Catalog

Quick-reference patterns for Phase 5 injection traversal and Phase 8 adversarial sequencing.
Use this reference when a pattern name is recognized but full trace logic would bloat the main review.

---

## Injection Classes

### SQL Injection

**Variants**: Classic, Blind (Boolean / Time-based), Error-based, Out-of-band, Second-order

**Second-order** is the most commonly missed: user input is stored safely, then later retrieved and concatenated into a query in a different code path. The injection point and the sink are in different files or services.

**Bypass patterns for apparent mitigations**:
- Parameterized query used for the `WHERE` clause but not for `ORDER BY`, `LIMIT`, or table/column names
- ORM `raw()` or `execute()` used alongside safe ORM methods — check all raw call sites
- Allowlist bypass: `'; DROP TABLE users; --` → `a'/**/OR/**/1=1--` (comment-based space bypass)
- Type coercion: integer parameter that is cast from string after the query is assembled

---

### Shell / Command Injection

**Indicators**: `subprocess(shell=True)`, `os.system`, `os.popen`, `exec()`, backtick evaluation, `child_process.exec()` (Node), `Runtime.exec()` (Java with string concat)

**Bypass patterns**:
- Argument injection: binary is safe, but user controls a flag (`--output /etc/passwd`)
- Environment variable injection: user data set as env var, script reads it unsanitized
- Filename injection: user controls filename passed to `tar`, `zip`, `convert`, etc. (`-o /path/to/write`)
- Null byte injection: `file.pdf\x00.php` — language sees `.pdf`, OS sees `.php`

---

### Path Traversal

**Pattern**: `base_path + user_input` without canonicalization and boundary check.

**Bypass patterns**:
- URL encoding: `%2e%2e%2f` → `../`
- Double encoding: `%252e%252e%252f`
- Unicode normalization: `..%c0%af` (UTF-8 overlong encoding)
- `os.path.join` behavior: `os.path.join("/safe/dir", "/etc/passwd")` returns `/etc/passwd` — absolute path wins

**Safe pattern**: `resolved = os.path.realpath(os.path.join(base, user_input))` then assert `resolved.startswith(base + os.sep)`.

---

### Server-Side Request Forgery (SSRF)

**Target resources**:
- Cloud metadata endpoints: `http://169.254.169.254/latest/meta-data/` (AWS), `http://metadata.google.internal/`
- Internal services: `http://localhost:6379` (Redis), `http://10.0.0.1/admin`
- File scheme: `file:///etc/passwd`
- Protocol smuggling: `gopher://`, `dict://`, `ftp://`

**Bypass patterns for IP allowlists**:
- DNS rebinding: domain resolves to allowed IP at check time, attacker IP at request time
- IPv6 encoding: `http://[::ffff:169.254.169.254]/`
- Decimal encoding: `http://2852039166/` (169.254.169.254 as decimal)
- Redirect chain: allowed URL redirects to internal resource

---

### Deserialization

**High-risk sinks by language**:

| Language | Dangerous sinks |
|----------|----------------|
| Python | `pickle.loads`, `yaml.load` (not `safe_load`), `shelve`, `marshal.loads` |
| Java | `ObjectInputStream.readObject`, `XStream`, `Jackson` with polymorphic typing enabled |
| PHP | `unserialize()`, `json_decode` with object casting |
| Ruby | `Marshal.load`, `YAML.load` (not `safe_load`) |
| Node.js | `node-serialize`, `serialize-javascript` with eval |

**Gadget chain principle**: the language runtime provides the execution primitive; the attacker just needs to find the right sequence of existing objects. Safe-looking code can be a gadget if its methods are called in the right order during deserialization.

---

### Template Injection (SSTI)

**Detection probes**:
- Jinja2: `{{7*7}}` → `49`; `{{config}}` → server config object
- Twig: `{{7*'7'}}` → `49`
- FreeMarker: `${7*7}` → `49`

**Code execution path**: Jinja2 → `{{''.__class__.__mro__[1].__subclasses__()}}` → find `subprocess.Popen` → RCE.

**Indicators**: User-controlled string passed to `.render()`, `Template(user_input)`, or template name resolution from user data.

---

### XML External Entity (XXE)

**Attack vectors**:
- Classic XXE: `<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>`
- Blind XXE via out-of-band channel: entity fetches attacker-controlled URL with exfiltrated data
- XXE via SVG, DOCX, XLSX, PDF — any format that embeds XML

**Indicators**: XML parsing with external entity processing enabled (default in many parsers). `xml.etree.ElementTree` in Python is safe; `lxml` with `resolve_entities=True` is not.

---

## Trust Boundary Attack Patterns

### Confused Deputy

An intermediary component (agent, API gateway, backend service) has permissions that exceed what the requester is authorized for. The attacker crafts a request that causes the intermediary to perform an action the attacker could not perform directly.

**Recognition**: Request path crosses a privilege boundary. The intermediary does not re-verify the caller's authorization for the action it is about to take.

---

### Time-of-Check / Time-of-Use (TOCTOU)

A security check and the guarded action are not atomic. Between the check and the use, an attacker modifies the resource.

**Classic pattern**:
```
if os.path.exists(file):       # check
    # attacker replaces symlink here
    open(file).read()          # use — now reads different file
```

**Recognition**: Any `check → act` pattern on shared mutable resources (files, database rows, cache entries) without locks or atomic operations.

---

### Insecure Direct Object Reference (IDOR)

The application exposes a reference to an internal object (ID, filename, account number) and does not verify that the requesting principal is authorized to access that specific object.

**Recognition**: `GET /api/documents/{id}` — does the handler verify that `id` belongs to the authenticated user, or does it fetch any record matching the ID?

---

### Mass Assignment

ORM or framework binds all user-supplied fields to a model object without an explicit allowlist. Attacker sets `is_admin=true`, `role=superuser`, or `balance=1000000` in the request body.

**Indicators**: `User.create(params)`, `Object.assign(user, req.body)`, Django `ModelForm` without `fields` restriction, Rails `params.permit` missing fields.

---

### JWT Algorithm Confusion

- **`alg: none`**: Attacker removes signature; server accepts unsigned token if `none` is not rejected.
- **RS256 → HS256 confusion**: Server public key is used as HMAC secret; attacker signs with the known public key.
- **`kid` injection**: Key ID parameter used in SQL query or file path to select verification key.

**Recognition**: JWT library configured to accept algorithm from the token header rather than enforcing a specific algorithm.

---

## Dependency Supply Chain Patterns

### Typosquatting
Package name is one character different from a popular package. Installed by developer typo or injected into dependency resolution.

### Dependency Confusion
Internal package name published to public registry with a higher version number. Build system fetches public package instead of internal one.

### Maintainer Takeover
Original maintainer transfers ownership or credentials are compromised. New maintainer publishes a version with malicious code.

**Recognition signals**: Package name close to popular package; very recent publish of new major version with no announcement; new maintainer email domain; install scripts in `package.json` `postinstall`.

---

## Cryptographic Weakness Patterns

| Weakness | Indicator |
|----------|-----------|
| Hardcoded IV | `AES.new(key, AES.MODE_CBC, b'\x00' * 16)` |
| ECB mode | `AES.new(key, AES.MODE_ECB)` — leaks block patterns |
| MD5 / SHA-1 for security | Used in MAC, password hash, or signature verification |
| Weak random | `random.random()` or `Math.random()` for token/nonce generation |
| Timing attack | String comparison of HMAC or token with `==` instead of `hmac.compare_digest` |
| Key in source | Any cryptographic key, HMAC secret, or JWT secret in a code file |
