# Documentation Organization

This document describes the organization of DocEX documentation and test scripts.

## Documentation Structure

### Main Documentation (`docs/`)

Active documentation for developers and system integrators:

- **Developer_Guide.md** - Main developer guide with setup, usage, and best practices
- **Platform_Integration_Guide.md** - Platform integration patterns and examples
- **API_Reference.md** - Complete API documentation
- **MULTI_TENANCY_GUIDE.md** - Multi-tenancy documentation
- **TENANT_PROVISIONING.md** - Tenant provisioning guide
- **S3_PATH_STRUCTURE.md** - S3 path structure documentation
- **CLI_GUIDE.md** - Command-line interface reference
- **DocBasket_Usage_Guide.md** - Basket operations guide
- **Release_Validation_Guide.md** - Release validation procedures
- **Test_Scripts_Summary.md** - Available test scripts
- **PERFORMANCE_IMPROVEMENTS_SUMMARY.md** - Performance improvements
- **DOCKER_SETUP.md** - Docker setup guide
- **LLM_ADAPTERS_GUIDE.md** - LLM adapters guide
- **TESTING_GUIDE.md** - Testing guide
- **OPENAI_API_KEY_SETUP.md** - OpenAI API key setup

### Design Documents (`docs/contributors/design/`)

Historical design documents, proposals, and implementation notes preserved for reference:

- Design documents (Docex_3_Design_Review.md, DocEX_Design.md, etc.)
- Implementation summaries and status documents
- Path resolver implementation history
- S3 implementation notes
- Assessments and proposals
- Configuration and naming recommendations
- Historical test results

See `docs/contributors/design/README.md` for details.

## Test Scripts Organization

### Root Directory

Essential test scripts that are commonly used:

- None currently (all moved to `scripts/test/` or `tests/`)

### `scripts/test/`

Integration and validation test scripts:

- `test_performance_improvements.py` - Performance testing
- `test_basket_file_operations.py` - Basket and file operations
- `test_docex3_postgres.py` - PostgreSQL integration tests
- `test_release_validation.py` - Release validation
- `test_issue_36_fixes.py` - Issue-specific tests
- `init_docex_postgres_test.py` - PostgreSQL initialization
- `integrate_docex_platform.py` - Platform integration example

### `tests/`

Unit tests and test suite:

- Standard pytest test files
- Test fixtures and utilities

### `examples/`

Example scripts demonstrating usage:

- Basic usage examples
- Processor examples
- RAG examples
- Multi-tenancy examples

## Script Usage

### Running Test Scripts

```bash
# From project root
python scripts/test/test_performance_improvements.py --tenant-id acme_corp --user-id test_user

# Or from scripts/test directory
cd scripts/test
python test_performance_improvements.py --tenant-id acme_corp --user-id test_user
```

### Running Unit Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_basic.py
```

## Documentation Updates

When adding new documentation:

1. **Active documentation** → Add to `docs/` root
2. **Design/proposal documents** → Add to `docs/contributors/design/`
3. **Test scripts** → Add to `scripts/test/` or `tests/` as appropriate
4. **Update this document** if structure changes

## Cleanup Guidelines

Documents should be moved to `docs/contributors/design/` if they:

- Are historical/archival
- Contain outdated information
- Are design proposals that were implemented
- Are implementation summaries for completed work
- Are test results from past releases

Documents should remain in `docs/` if they:

- Are actively maintained
- Provide current usage guidance
- Are referenced by other active documents
- Are part of the developer workflow

