# DocEX Improvement Backlog

## Context

This backlog captures the remaining DocEX quality and design improvements identified while integrating DocEX into `llamasee-meta` and validating both the local and AWS-backed environments.

Recent progress already completed:

- added Ruff configuration for the touched DocEX hot-path files
- removed the duplicate `transaction()` definition in `docex/db/connection.py`
- made `DocBasket` storage initialization lazy
- made `Document` storage initialization lazy
- lowered storage-service constructor logging from `INFO` to `DEBUG`
- added lightweight metadata-first document search support
- added Postgres-backed regression tests proving metadata reads stay off the storage path
- fixed a Postgres initialization regression caused by a branch-local `create_engine` import

What remains is the larger cleanup needed to make DocEX predictable, fast, and safer to embed as a library.

## Remaining Work

### 1. Separate destructive setup from runtime initialization

Problem:
- `DocEX.setup()` still performs table reset / creation behavior that is too destructive for shared or integration-test environments.
- Library consumers cannot safely use `setup()` against a populated database.

Requested improvement:
- split configuration setup from schema management
- introduce a non-destructive runtime initialization path
- move schema reset / bootstrap logic into explicit admin-only commands

Acceptance criteria:
- `DocEX.setup()` or its replacement can be used in tests and applications without dropping existing tables
- schema creation/reset is opt-in and clearly named

### 2. Create explicit read-only and write DB APIs

Problem:
- read paths and write paths are still too easy to mix
- session lifecycle is harder to reason about than it should be

Requested improvement:
- expose a clear read session helper and a separate write transaction helper
- keep read-only search/list/count operations on the read helper only

Acceptance criteria:
- metadata list/search/count methods do not commit transactions
- tests clearly cover read-only vs write behavior

### 3. Make basket and document reads lightweight by default

Problem:
- some APIs still default to heavyweight runtime objects even when callers only need metadata
- wrapper layers still need to work around this to stay performant

Requested improvement:
- promote lightweight record-returning APIs to first-class status
- keep full `DocBasket` / `Document` objects for mutation and content retrieval only

Acceptance criteria:
- `list_baskets_with_metadata()` and document metadata search/list paths are documented as the preferred fast path
- callers can fully inspect metadata without constructing content-capable runtime objects

### 4. Add first-class record models for lightweight reads

Problem:
- lightweight APIs currently return dictionaries
- the API shape is looser than it should be for library consumers

Requested improvement:
- add `BasketRecord` and `DocumentRecord` types
- return typed records from metadata-first APIs

Acceptance criteria:
- lightweight list/search methods return stable typed results
- wrappers like `DocEXStore` can depend on these models directly

### 5. Normalize and validate basket storage configuration

Problem:
- stale or malformed basket storage configuration can break later writes
- local integration testing surfaced old baskets with mismatched storage config

Requested improvement:
- validate basket storage configuration at read/use time
- add repair or migration helpers for legacy storage-config shapes

Acceptance criteria:
- stale basket config produces actionable diagnostics
- optionally provide a migration utility for existing baskets

### 6. Tighten storage initialization behavior

Problem:
- storage is now lazy on the main hot path, but initialization rules are still spread across multiple layers

Requested improvement:
- centralize storage initialization semantics
- ensure constructors do not perform hidden storage mutations

Acceptance criteria:
- basket/document construction alone never touches filesystem or S3
- content/store/delete paths are the only ones that initialize storage

### 7. Expand regression coverage for library-safe behavior

Problem:
- recent fixes are covered, but not yet broadly enough

Requested improvement:
- extend tests around:
  - non-destructive runtime initialization
  - read-only metadata APIs
  - basket config validation
  - multi-tenant Postgres behavior
  - wrapper integration with `llamasee-meta`

Acceptance criteria:
- targeted tests exist for the main integration guarantees
- Postgres-backed tests remain runnable with local `.env` configuration

### 8. Continue Ruff rollout beyond the touched hot-path files

Problem:
- Ruff now passes on the touched DocEX files, but not the wider submodule
- line-length debt is still intentionally deferred

Requested improvement:
- expand Ruff coverage gradually by module
- keep `E501` deferred until broader formatting cleanup is planned

Acceptance criteria:
- hot-path modules stay Ruff-clean
- each follow-up cleanup expands the enforced surface area

## Suggested Execution Order

1. non-destructive initialization split
2. read-only vs write DB API separation
3. typed lightweight record models
4. basket storage-config validation / migration
5. broader regression coverage
6. wider Ruff rollout

## Why This Matters For `llamasee-meta`

`llamasee-meta` depends on DocEX as an embedded library, not just as a standalone tool. That means:

- runtime setup must be safe in shared environments
- read/search latency must stay DB-first and avoid storage work
- metadata-heavy workflows need stable lightweight APIs
- local and AWS-backed verification must behave consistently

These improvements reduce adapter complexity in `tools/llamasee_meta/metadata_store/docex_store.py` and make future integration changes much safer.
