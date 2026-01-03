# DocEX 3.0 Design Document

**Status:** Draft
**Target Release:** v3.0
**Audience:** Maintainers, Contributors, Platform Integrators
**Last Updated:** 2026-01-01

---

## 1. Executive Summary

DocEX 3.0 is a **major architectural release** that formalizes DocEX as a **secure, embeddable document execution engine** with explicit multi-tenancy and strong isolation guarantees.

Version 3.0 removes implicit behaviors introduced in early versions and replaces them with:

* Explicit tenant provisioning
* Deterministic system bootstrap
* Clear runtime security boundaries

The result is a library that is:

* Safer by default
* Easier to operate at scale
* More predictable for open-source users and enterprise adopters

---

## 2. Design Goals

DocEX 3.0 is designed to:

1. Make **multi-tenancy a first-class primitive**
2. Separate **system bootstrap**, **tenant provisioning**, and **runtime execution**
3. Enforce tenant boundaries without SaaS assumptions
4. Remain embeddable in:

   * SaaS platforms
   * Internal tools
   * Batch jobs and agents
5. Reduce operational ambiguity by eliminating implicit defaults

---

## 3. Non-Goals

DocEX 3.0 explicitly does NOT aim to:

* Provide authentication or identity management
* Implement tenant billing or lifecycle workflows
* Perform runtime schema migrations
* Become a hosted service

---

## 4. Architectural Pillars

### 4.1 Explicitness Over Convenience

All critical boundaries (tenant, user, storage) must be:

* Explicit in configuration
* Explicit in APIs
* Explicit at runtime

Silent fallback behavior is removed.

---

### 4.2 Library-First Philosophy

DocEX remains a **library**, not a framework:

* No global state
* No middleware assumptions
* No request lifecycle coupling

---

### 4.3 Boring Infrastructure

Provisioning, isolation, and configuration are designed to be:

* Predictable
* Deterministic
* Easy to reason about

---

## 5. High-Level Architecture

```
+------------------------+
|   Host Application     |
| (SaaS / Tool / Agent)  |
+-----------+------------+
            |
            v
+------------------------+
|        DocEX 3.0       |
|------------------------|
| System Bootstrap       |
| Tenant Provisioning    |
| Runtime Execution      |
| Isolation Strategies   |
+-----------+------------+
            |
            v
+------------------------+
| Storage Backends       |
| (DB, S3, FS, etc.)     |
+------------------------+
```

---

## 6. Lifecycle Model

### 6.1 System Bootstrap

Performed once per environment.

**Command:**

```bash
docex init
```

Responsibilities:

* Generate `docex.yaml`
* Validate storage connectivity
* Create bootstrap tenant
* Initialize system metadata

System bootstrap must be:

* Idempotent
* Environment-scoped

---

### 6.2 Tenant Provisioning

Performed explicitly per tenant.

**API:**

```python
TenantProvisioner.create(
    tenant_id="acme",
    display_name="Acme Corp"
)
```

Responsibilities:

* Create tenant isolation boundary
* Register tenant metadata
* Validate uniqueness

No runtime migrations are performed.

---

### 6.3 Runtime Execution

All runtime operations require explicit context.

```python
DocEX(
  user_context=UserContext(
    user_id="u123",
    tenant_id="acme",
    roles=["user"]
  )
)
```

Rules:

* Tenant context is mandatory when multi-tenancy is enabled
* No implicit or default tenant resolution

---

## 7. Configuration Model

DocEX 3.0 uses a single canonical configuration file.

```yaml
config_version: 1

multi_tenancy:
  enabled: true
  isolation_strategy: schema
  bootstrap_tenant:
    id: system
    schema: docex_system

database:
  type: postgres
  database: docex

storage:
  documents:
    type: s3
    tenant_scoped: true
```

Configuration is:

* Versioned
* GitOps-friendly
* Environment-specific

---

## 8. Tenant Isolation

### 8.1 Isolation Strategies

| Strategy            | Status    | Notes                    |
| ------------------- | --------- | ------------------------ |
| Schema-per-tenant   | Supported | Default for v3.0         |
| Database-per-tenant | Planned   | Regulated environments   |
| Row-level isolation | Planned   | Cost-sensitive use cases |

---

### 8.2 Bootstrap Tenant

The bootstrap tenant:

* Owns system metadata
* Is never used for business operations
* Is explicitly flagged

---

## 9. Security Model

### 9.1 UserContext

UserContext is the **sole carrier** of identity and authorization.

Fields:

* user_id
* tenant_id
* roles

---

### 9.2 Enforcement Rules

* No operation without tenant context (when enabled)
* No cross-tenant access
* Fail-fast on violations

---

## 10. Backward Compatibility & Breaking Changes

### 10.1 Removed in v3.0

* Implicit default tenant
* Runtime schema creation
* Global tenant state

---

### 10.2 Migration from v2.x

Required actions:

1. Run `docex init`
2. Provision tenants explicitly
3. Pass UserContext at runtime

---

## 11. Operational Characteristics

* Deterministic provisioning
* Predictable isolation
* Clear error semantics

DocEX 3.0 favors **safety over convenience**.

---

## 12. Risks & Mitigations

| Risk                | Mitigation             |
| ------------------- | ---------------------- |
| Increased verbosity | Strong docs & examples |
| Breaking changes    | Clear upgrade guide    |
| User friction       | Opt-in in v2.x         |

---

## 13. Future Work (Post-3.0)

* Tenant deletion & suspension
* Enhanced audit pipelines
* Pluggable authorization policies
* Advanced isolation strategies

---

## 14. Conclusion

DocEX 3.0 establishes a **clear, explicit, and secure foundation** for long-term growth.

By enforcing boundaries early, DocEX becomes:

* Easier to embed
* Safer to operate
* More trustworthy for enterprise and open-source users alike

---
