# RFC-0001: Multi-Tenancy Architecture for DocEX

**Status:** Draft
**Target Version:** v3.0
**Authors:** DocEX Maintainers
**Last Updated:** 2026-01-01

---

## 1. Motivation

DocEX is evolving into a reusable **document execution engine** that must safely support:

* Multiple organizations (tenants)
* Multiple users per tenant
* Multiple storage backends

Early versions implicitly assumed single-tenant or weak isolation. As adoption grows, this creates risks:

* Accidental cross-tenant access
* Operational fragility
* Ambiguous security boundaries

This RFC proposes a **clear, explicit, library-first multi-tenancy architecture** that is compatible with DocEX’s open-source goals and avoids SaaS lock-in.

---

## 2. Goals

This RFC aims to:

* Define **tenant isolation as a core primitive**
* Separate **tenant mechanics** from **tenant policy**
* Enable deterministic provisioning without runtime migrations
* Provide a stable foundation for security, audit, and extensibility

---

## 3. Non-Goals

DocEX explicitly does **not** aim to:

* Manage authentication or identity providers
* Provide billing, onboarding, or tenant lifecycle workflows
* Act as a hosted SaaS platform
* Support runtime schema migrations

---

## 4. Definitions

* **Tenant**: A logical isolation boundary for data and operations
* **Bootstrap Tenant**: A system-owned tenant used for metadata and provisioning
* **UserContext**: Runtime identity and authorization carrier
* **Isolation Strategy**: Mechanism by which tenant data is isolated

---

## 5. Architecture Overview

### 5.1 Tenant as a First-Class Concept

Tenants are:

* Explicitly provisioned
* Registered in system metadata
* Required for all multi-tenant runtime operations

No implicit or default tenant behavior is permitted.

---

### 5.2 Bootstrap vs Business Tenants

A **bootstrap tenant** is created during system initialization.

Responsibilities:

* Own system metadata
* Anchor provisioning operations

Rules:

* Must never be used for end-user document operations
* Must be explicitly flagged (`is_system = true`)

---

## 6. Provisioning Model (No Migrations)

### 6.1 Initialization (`docex init`)

Responsibilities:

* Generate base configuration
* Validate storage connectivity
* Create bootstrap tenant schema
* Create tenant registry

Initialization is:

* One-time
* Idempotent
* Environment-scoped

---

### 6.2 Tenant Provisioning

Tenant creation is explicit and deterministic.

```python
TenantProvisioner.create(
    tenant_id="acme",
    display_name="Acme Corp"
)
```

Provisioning must:

* Create isolation boundary (schema, db, etc.)
* Register tenant metadata
* Fail fast on conflicts

No runtime migrations are supported; schema is fixed at provision time.

---

## 7. Isolation Strategies

DocEX supports pluggable isolation strategies.

### 7.1 Schema-per-Tenant (Initial)

* One schema per tenant
* Strong isolation
* Operationally simple

### 7.2 Future Strategies (Out of Scope)

* Database-per-tenant
* Row-level isolation

---

## 8. Runtime Enforcement

### 8.1 UserContext Contract

```python
UserContext(
  user_id="u123",
  tenant_id="acme",
  roles=["admin"]
)
```

Rules:

* Required when multi-tenancy is enabled
* Absence results in hard failure

---

### 8.2 No Implicit Context

DocEX must never:

* Infer tenant from environment
* Fall back to bootstrap tenant
* Use global mutable tenant state

---

## 9. Backward Compatibility Strategy

* v2.x remains functional but deprecated
* v3.0 introduces explicit multi-tenancy
* Implicit single-tenant behavior removed

See Section 11 for details.

---

## 10. Alternatives Considered

### 10.1 Implicit Tenant Context

Rejected due to:

* Security risk
* Hidden coupling
* Poor auditability

### 10.2 SaaS-Centric Tenant Manager

Rejected due to:

* Overreach for a library
* Reduced embeddability

---

## 11. Migration to v3.0

### Required Changes:

* Explicit tenant provisioning
* Explicit UserContext in runtime calls
* Updated configuration format

### Deprecated Behaviors:

* Global default tenant
* Auto-created schemas at runtime

---

## 12. Open Questions

* Should tenant deletion be supported?
* Should system tenant be configurable?

---

## 13. Summary

This RFC establishes a **secure, explicit, and boring-by-design** multi-tenancy foundation for DocEX.

By prioritizing clarity over convenience, DocEX remains:

* Open-source friendly
* Enterprise safe
* Future extensible

---
