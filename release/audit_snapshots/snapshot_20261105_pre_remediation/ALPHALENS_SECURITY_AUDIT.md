# ALPHALENS — INDEPENDENT SECURITY & CREDENTIAL AUDIT REPORT

**Platform**: AlphaLens NSE Market Research Platform (Private Localhost Edition)  
**Host**: Windows 11 (`BHAVY17`)  
**Audit Timestamp**: 2026-11-05T08:18:00 UTC (13:48 IST)  
**Security Verdict**: **`SECURITY_AUDIT_PASSED`**  
**Evidence Artifact**: `release/alphalens_security_audit.json`

---

## 1. Executive Summary

An independent security evaluation of the complete AlphaLens codebase, configuration files, network projection, authentication mechanisms, and secret isolation was conducted.

The platform complies with all private research security invariants:
- **Zero Secret Exposure**: 1,266 tracked Git files scanned; 0 live secrets, private keys, or credentials found.
- **Strict Loopback Binding**: The backend FastAPI server binds exclusively to `127.0.0.1:8041`, refusing external or public network interfaces (`0.0.0.0`).
- **CORS Local Isolation**: Cross-Origin Resource Sharing is strictly constrained to `http://127.0.0.1:8041`. Unapproved browser origins are rejected with HTTP 403.
- **Enterprise Cookie & Session Security**: Session cookies enforce `HttpOnly=True`, `SameSite=Strict`, custom path scoping (`/api/v1`), and automatic session revocation/rotation on authentication.
- **CSRF Defense**: All mutating HTTP methods (`POST`, `PUT`, `DELETE`) require an unguessable 43-character `x-csrf-token` validated via constant-time comparison (`secrets.compare_digest`).
- **SQL Injection Prevention**: All queries across SQLite ledgers and stores use strict parameterized bindings (`?`). Zero dynamic SQL string formatting.

---

## 2. Network & Loopback Isolation

| Security Property | Configured Value | Verification Status | Notes |
| :--- | :--- | :--- | :--- |
| **Binding Host** | `127.0.0.1` | **PASSED** | Never exposed to LAN or WAN |
| **Port** | `8041` | **PASSED** | Single-purpose loopback port |
| **Allowed CORS Origins** | `["http://127.0.0.1:8041"]` | **PASSED** | Unauthorized origins rejected with 403 |
| **Transport** | Loopback HTTP | **PASSED** | Safe for local-only private research |
| **Process Model** | Single Operator | **PASSED** | Scoped to interactive operator session |

---

## 3. Authentication & Session Architecture

1. **Local Account Storage**:
   - Operator credentials stored in encrypted/hashed SQLite format (`auth_root`).
   - Passwords hashed using industry-standard salted derivation.
   - Enforces password and username policy rejection rules.
2. **Context-Gated Login**:
   - The login endpoint requires an explicit local context header (`x-alphalens-local: p21`).
   - External automated bots or generic requests without local context are immediately rejected with HTTP 403 `LOGIN_CONTEXT_REQUIRED`.
3. **Session Lifecycle**:
   - Generated session tokens have 256-bit entropy.
   - Absolute session timeout enforced (`ABSOLUTE_SECONDS`).
   - Session tokens are strictly rotated upon successful login to prevent fixation attacks.
   - Session cookies carry `HttpOnly=True` and `SameSite="strict"`.

---

## 4. Secret Isolation & Upstox Integration Protection

1. **Repository Cleanliness**:
   - Automated regex scanning of all 1,266 tracked repository files confirmed **0 live credentials**.
   - Synthetic values in unit tests are strictly prefixed (`TEST_ONLY_...`, `MOCK_...`).
2. **Upstox API Token Security**:
   - API tokens are held strictly in local protected storage (`D:\al-research\p28-runtime\provider-state`).
   - File permissions are restricted to the local Windows operator account (`Dell`).
   - Token access is gated behind rate-limiting controllers (600 requests/run, 1,800 requests/day).

---

## 5. Security Verdict

The AlphaLens local research installation is safe, robust, and secure for ongoing private quantitative research.
