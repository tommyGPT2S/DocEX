# Security Best Practices for DocEX Examples

This document outlines the security best practices implemented across all DocEX examples.

## UserContext Usage

All examples now demonstrate proper use of `UserContext` for audit logging and security. The `UserContext` class provides:

- **User Identification**: Track which user performed operations
- **Audit Logging**: All operations are logged with user context
- **Multi-tenant Support**: Enable tenant isolation when `tenant_id` is provided
- **Role-based Context**: Support for application-layer access control

### Basic Usage

```python
from docex import DocEX
from docex.context import UserContext

# Create UserContext for audit logging
user_context = UserContext(
    user_id="example_user",
    user_email="user@example.com",
    tenant_id="example_tenant",  # Optional: for multi-tenant applications
    roles=["user"]  # Optional: for application-layer access control
)

# Initialize DocEX with UserContext
docEX = DocEX(user_context=user_context)
```

### Production Integration

In production applications, `UserContext` should be created from your authentication system:

```python
# Example: From JWT token or session
def get_user_context_from_request(request):
    """Extract user context from authenticated request"""
    return UserContext(
        user_id=request.user.id,
        user_email=request.user.email,
        tenant_id=request.user.tenant_id,
        roles=request.user.roles
    )

# Use in your application
user_context = get_user_context_from_request(request)
docEX = DocEX(user_context=user_context)
```

## Multi-Tenancy Support

DocEX supports two multi-tenancy models:

### Model A: Row-Level Isolation (Shared Database)
- All tenants share the same database
- Logical isolation using `tenant_id` columns
- **Status**: Proposed (not yet implemented)

### Model B: Database-Level Isolation (Per-Tenant Database) ✅
- Each tenant has its own database (SQLite) or schema (PostgreSQL)
- Physical data isolation
- **Status**: Implemented and ready for production

### Configuration

Enable database-level multi-tenancy in `~/.docex/config.yaml`:

```yaml
security:
  multi_tenancy_model: database_level
  tenant_database_routing: true

database:
  type: postgresql
  postgres:
    host: localhost
    port: 5432
    database: docex
    user: postgres
    password: postgres
    schema_template: "tenant_{tenant_id}"  # Schema per tenant
```

### Usage Example

```python
from docex import DocEX
from docex.context import UserContext

# Tenant 1 - automatically routes to tenant1 schema
user_context1 = UserContext(user_id="alice", tenant_id="tenant1")
docEX1 = DocEX(user_context=user_context1)
basket1 = docEX1.create_basket("invoices")  # Created in tenant1 schema

# Tenant 2 - automatically routes to tenant2 schema (isolated)
user_context2 = UserContext(user_id="bob", tenant_id="tenant2")
docEX2 = DocEX(user_context=user_context2)
basket2 = docEX2.create_basket("invoices")  # Created in tenant2 schema
```

## Updated Examples

The following examples have been updated to include security best practices:

1. **basic_usage.py** - Basic operations with UserContext
2. **hello_world.py** - Minimal example with UserContext
3. **llm_adapter_usage.py** - LLM processing with UserContext
4. **vector_search_example.py** - Vector search with UserContext
5. **pdf_invoice_to_purchase_order.py** - Invoice processing with UserContext
6. **route_management.py** - Route management with UserContext
7. **route_file_transfer.py** - File transfer with UserContext
8. **processor_csv_to_json.py** - CSV processing with UserContext

## Security Considerations

### Access Control

DocEX provides audit logging infrastructure, but **access control is enforced at the application layer** by default. This design allows:

- Flexibility to implement any access control model (RBAC, ABAC, etc.)
- Integration with existing IAM/RBAC systems
- Clear separation of concerns

### Example: Application-Layer Access Control

```python
# Application layer enforces access control
user_context = UserContext(user_id="alice", tenant_id="tenant1", roles=["admin"])

# Check permissions before calling DocEX
if not user_has_permission(user_context, "read", basket_id):
    raise PermissionError("Access denied")

# Then call DocEX (which logs the operation)
docEX = DocEX(user_context=user_context)
basket = docEX.get_basket(basket_id)
```

### Credential Management

**Best Practice**: Never hardcode credentials. Use environment variables or secret management systems:

```python
# Good: Use environment variables
api_key = os.getenv('OPENAI_API_KEY')
aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')

# Bad: Hardcoded credentials
api_key = "sk-..."  # ❌ Never do this
```

## Additional Resources

- **Multi-Tenancy Guide**: See `docs/MULTI_TENANCY_GUIDE.md`
- **Security Design**: See `docs/DocEX_Design.md` Section 11
- **Developer Guide**: See `docs/Developer_Guide.md` for configuration details

## Summary

✅ **Always use UserContext** for audit logging and security  
✅ **Provide tenant_id** for multi-tenant applications  
✅ **Enforce access control** at the application layer  
✅ **Use environment variables** for credentials  
✅ **Enable database-level multi-tenancy** for strict compliance requirements

