# Bootstrap Tenant Naming Recommendations

## Your Proposal: `_docex_system_`

**Analysis:** This is a solid choice with clear benefits.

### ✅ Pros:
- **Highly distinctive:** Triple underscores make it unmistakably system-owned
- **Namespace protection:** Very unlikely to conflict with user-created tenant IDs
- **Self-documenting:** Clearly indicates it's a DocEX system tenant
- **Easy to filter:** Simple regex pattern to reject: `^_.*_$` or `^_docex_`
- **Database-friendly:** Works well in PostgreSQL (quoted) and SQLite identifiers

### ⚠️ Considerations:
- **Verbose:** Longer than necessary (but clarity > brevity for system tenants)
- **Underscore handling:** Need to ensure proper quoting in SQL (PostgreSQL requires quotes for special chars)

---

## Alternative Options

### Option 1: `__system__` (Double Underscore)
**Python "dunder" convention**

**Pros:**
- ✅ Follows Python convention for special names
- ✅ Short and clear
- ✅ Easy to filter: `^__.*__$`

**Cons:**
- ⚠️ Less explicit about being DocEX-specific
- ⚠️ Could conflict if users adopt similar naming

**Verdict:** Good, but less explicit than your proposal.

---

### Option 2: `docex_system` (Simple)
**Matches design doc schema name**

**Pros:**
- ✅ Simple and clean
- ✅ Matches the schema name pattern in design doc
- ✅ No special character handling needed

**Cons:**
- ⚠️ Could conflict with user tenant named "docex_system"
- ⚠️ Less obviously "system-only"

**Verdict:** Too permissive - users might accidentally use this name.

---

### Option 3: `_system` (Single Underscore Prefix)
**Unix-style hidden/internal convention**

**Pros:**
- ✅ Common convention for "internal" things
- ✅ Short
- ✅ Easy to filter: `^_`

**Cons:**
- ⚠️ Too generic - could conflict with user tenants starting with `_`
- ⚠️ Less explicit about being DocEX-specific

**Verdict:** Too permissive - users might use `_mytenant`.

---

### Option 4: `.system` (Dot Prefix)
**Hidden file convention**

**Pros:**
- ✅ Very distinctive
- ✅ Unix convention for hidden/system files

**Cons:**
- ❌ **Problematic in SQL:** Dots in identifiers require special handling
- ❌ Not standard for database naming
- ❌ Could cause issues with some SQL parsers

**Verdict:** ❌ **Not recommended** - database compatibility issues.

---

### Option 5: `__docex_system__` (Double Underscore with DocEX)
**Combination approach**

**Pros:**
- ✅ Python dunder convention
- ✅ DocEX-specific
- ✅ Highly distinctive

**Cons:**
- ⚠️ Slightly longer than `__system__`
- ⚠️ Still less explicit than triple underscore

**Verdict:** Good middle ground, but your proposal is clearer.

---

## Recommendation: **`_docex_system_`** ✅

Your proposal `_docex_system_` is the **best choice** for the following reasons:

### 1. **Maximum Clarity**
- Immediately obvious it's a system tenant
- No ambiguity about ownership (DocEX-specific)
- Triple underscores are a strong visual signal

### 2. **Collision Resistance**
- Extremely unlikely users would create a tenant with this exact name
- The pattern `_docex_*_` can be reserved for system use

### 3. **Easy Enforcement**
```python
# Simple validation
SYSTEM_TENANT_PATTERN = r'^_docex_.*_$'
SYSTEM_TENANT_ID = '_docex_system_'

def is_system_tenant(tenant_id: str) -> bool:
    """Check if tenant ID is a system tenant"""
    return tenant_id == SYSTEM_TENANT_ID or re.match(SYSTEM_TENANT_PATTERN, tenant_id)

def reject_system_tenant_for_business_ops(tenant_id: str):
    """Reject system tenant for business operations"""
    if is_system_tenant(tenant_id):
        raise ValueError(f"System tenant '{tenant_id}' cannot be used for business operations")
```

### 4. **Database Compatibility**
```python
# PostgreSQL - quoted identifier
schema_name = '"_docex_system_"'  # or use search_path

# SQLite - works as-is
database_path = 'storage/_docex_system_/docex.db'
```

### 5. **Future Extensibility**
If you need more system tenants later:
- `_docex_system_` - Main system tenant
- `_docex_audit_` - Audit logs (if separated)
- `_docex_migration_` - Migration metadata (if needed)

All follow the same pattern and are easy to identify.

---

## Implementation Suggestion

### Configuration Default:
```yaml
multi_tenancy:
  enabled: true
  isolation_strategy: schema
  bootstrap_tenant:
    id: _docex_system_  # ← Your proposed name
    display_name: "DocEX System"
    schema: docex_system  # PostgreSQL schema (can be different from tenant_id)
```

**Note:** The `schema` name can be simpler (`docex_system`) since it's just a PostgreSQL identifier, while the `tenant_id` (`_docex_system_`) is used in application logic and needs to be more distinctive.

### Validation Code:
```python
# Constants
SYSTEM_TENANT_ID = '_docex_system_'
SYSTEM_TENANT_PATTERN = r'^_docex_.*_$'

class TenantProvisioner:
    @staticmethod
    def create(tenant_id: str, display_name: str):
        # Reject system tenant pattern
        if re.match(SYSTEM_TENANT_PATTERN, tenant_id):
            raise ValueError(
                f"Tenant ID '{tenant_id}' matches system tenant pattern. "
                f"System tenant IDs are reserved."
            )
        # ... rest of provisioning

class DocEX:
    def __init__(self, user_context: UserContext):
        # Reject system tenant for business operations
        if user_context.tenant_id == SYSTEM_TENANT_ID:
            raise ValueError(
                f"System tenant '{SYSTEM_TENANT_ID}' cannot be used for business operations. "
                f"Use a provisioned business tenant instead."
            )
        # ... rest of initialization
```

---

## Final Verdict

**✅ Use `_docex_system_` as the bootstrap tenant ID**

This name provides:
- ✅ Maximum clarity and self-documentation
- ✅ Strong collision resistance
- ✅ Easy validation and filtering
- ✅ Database compatibility
- ✅ Future extensibility

**Alternative if you want shorter:** `__docex_system__` (double underscore) is acceptable but less explicit.

**Not recommended:** `system`, `docex_system`, or `_system` - too permissive and collision-prone.

---

## Summary Table

| Option | Clarity | Collision Risk | DB Compat | Recommendation |
|--------|---------|----------------|-----------|----------------|
| `_docex_system_` | ⭐⭐⭐⭐⭐ | Very Low | ✅ | ✅ **BEST** |
| `__docex_system__` | ⭐⭐⭐⭐ | Low | ✅ | ✅ Good |
| `__system__` | ⭐⭐⭐ | Low | ✅ | ⚠️ Acceptable |
| `docex_system` | ⭐⭐ | Medium | ✅ | ❌ Too permissive |
| `_system` | ⭐⭐ | High | ✅ | ❌ Too permissive |
| `.system` | ⭐⭐⭐ | Very Low | ❌ | ❌ DB issues |

