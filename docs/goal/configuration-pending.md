# Configuration Pending

This note tracks behavior that should become versioned configuration but is
currently hardcoded in code, environment variables, seed data, or runtime state.

Use it to separate reusable defaults from mutable operational data.

## Rules

- Add an item when business or product behavior is hardcoded.
- Name the current hardcoded location.
- Name the intended configuration owner and file/store.
- Explain what remains runtime state.
- Do not move behavior into configuration without tests and owner agreement.

## Current Configuration-Controlled Areas

- `<area>`: `<path or store>`

## Main Gaps

### <Area Name>

Current hardcoded locations:

- `<path>`

Move into:

```text
<config-path-or-store>
```

The configuration should define:

- `<default, label, threshold, mapping, workflow, or policy>`

Runtime storage should keep:

- `<user edits, generated artifacts, active versions, audit events, etc.>`

## Configuration Versus Runtime Boundary

Use versioned configuration for defaults:

- product defaults
- tenant or environment defaults
- workflow shapes
- labels and display order
- adapter manifests
- default prompt, model, or tool bindings
- thresholds, scoring rules, and policy defaults

Use runtime storage for mutable state:

- user edits
- generated artifacts
- uploaded files
- active versions selected by admins
- event history
- audit records
- job results
- per-session state

## Priority

1. `<highest impact configuration gap>`
2. `<next gap>`
3. `<next gap>`
