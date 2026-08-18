# <Feature / Workstream> Handoff

Date: `<YYYY-MM-DD>`

## New Chat Startup

Paste this into the next chat:

```text
Continue DocEX <feature/workstream> work.

First read:
1. <repo>/docs/goal/goal.md
2. <repo>/docs/goal/handoffs/<YYYY-MM-DD>-<feature-slug>.md
3. <repo>/docs/goal/features/<feature-slug>/feature.md

Preserve existing behavior unless I explicitly ask to change it.
```

## Product Decisions

- `<Decision that should survive the handoff.>`

## Stable Contracts

- `<API, UI, data, file, schema, event, or external contract that must be kept.>`

## What Happened

- `<Implemented, changed, tested, discovered, or decided.>`

## Important Corrections

- `<Wrong path that was rejected or corrected.>`
- `<Misleading assumption to avoid.>`

## Current Implementation Direction

1. `<Next architectural or implementation direction.>`
2. `<Next step.>`
3. `<Next step.>`

## Files To Inspect

- `<path>`

## Verification Commands Used

```bash
<command>
```

Result: `<passed / failed / partial>`.

## Local Server Context

- Frontend: `<url>`
- Backend: `<url>`
- Other services: `<url or command>`

## Next Suggested Workflow

1. Re-read the goal file and relevant feature spec.
2. Audit the current diff and old behavior.
3. Implement the next smallest change.
4. Run focused tests.
5. Update the feature spec and this handoff.
