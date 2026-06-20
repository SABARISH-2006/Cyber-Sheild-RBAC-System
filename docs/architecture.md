# RBAC Security Portal: System Architecture

This document describes the security model, system components, and architectural workflows implemented in the Cyber-Shield Role-Based Access Control (RBAC) cybersecurity system.

---

## 1. Security Threat Model & Mitigations

### 1.1 Password Cryptography
- **Threat**: Database compromise leading to user credential leakage.
- **Mitigation**: Passwords are not stored as plain text. Instead, they are hashed using **Argon2id** or **bcrypt** with a minimum work factor of 12 (as seeded in default user data). 

### 1.2 SQL Injection (SQLi)
- **Threat**: Malicious user inputs executing arbitrary queries on the database.
- **Mitigation**: Database interfaces strictly use parameter binding (via `mysql2/promise` statement preparers). No query parameters are concatenated as raw strings.

### 1.3 JWT Hijacking & Token Revocation
- **Threat**: Compromised JWT tokens remain valid until expiration, allowing attackers unauthorized access.
- **Mitigation**: The system implements **active session tracking** (`user_sessions` table). 
  - On login, a SHA-256 hash of the generated JWT is recorded.
  - On every request, the authorization middleware validates that the token hash matches a live record.
  - On logout, the token hash is deleted, immediately revoking access.

### 1.4 Brute Force / Denial of Service
- **Threat**: High frequency login requests cracking passwords or exhausting database pool connections.
- **Mitigation**: Rate limiters are registered:
  - Global API rate limiter (`100` requests/15 mins per IP).
  - Authentication specific rate limiter (`10` requests/15 mins per IP).
  - Explicit payload sizing limits (`10kb` limit on JSON parses) to block request bloating.

---

## 2. RBAC Model (Resource-Action Mapping)

Rather than checking role strings directly in code (e.g., `if (role == 'Admin')`), which is fragile, the system utilizes **fine-grained permissions** mapped to **roles**, which are then assigned to **users**.

```
[User] --------> (assigned) --------> [Role] --------> (maps to) --------> [Permission] (Resource:Action)
```

### 2.1 Default Matrix

| Role | Resource Permissions | Cybersecurity Actions | Description |
|---|---|---|---|
| **SuperAdmin** | `user:*`, `role:*`, `logs:*`, `system:*`, `audit:*` | `network:scan`, `system:configure` | Full unrestricted control |
| **SecurityAdmin** | `user:*`, `role:*`, `logs:*`, `system:*` | `system:configure` | Security parameter and user maintenance |
| **Analyst** | `user:read`, `role:read`, `logs:view` | `network:scan` | Operation scanning & log observation |
| **Auditor** | `user:read`, `role:read`, `audit:read`, `logs:view` | None | Read-only compliance auditor |

---

## 3. Compliance and Audit Trails

Every administrative action (user creation, suspension, updates) and authentication change (successful login, failures, unauthorized attempts) triggers an **immutable audit log** entry.
- Audit logs contain: `user_id`, `action`, `resource`, `details` (JSON payload detailing changes), `ip_address`, `status` (success/failure), and `created_at`.
- Failed authorization checks (e.g. an Analyst attempting to delete a user) write a high-priority `UNAUTHORIZED_ACCESS_ATTEMPT` failure log to flag potential insider threats.
