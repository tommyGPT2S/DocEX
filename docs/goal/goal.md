# DocEX Goal

Root contract for `DocEX` work.

Read this before coding, debugging, testing, reviewing, or changing workflow
behavior.

Paths are relative to the project repo root unless explicitly marked absolute.

Use `docs/goal/features/index.md` to find feature specs.
Keep detailed feature behavior in `docs/goal/features/<feature-slug>/feature.md`.
Keep this file short: shared rules, workflow, verification, protected
contracts, and the feature-index pointer only.

## Critical Rules

These rules are mandatory. They override lower sections when wording conflicts.
Keep this section to exactly 10 bullets unless the owner approves changing the
critical set.

- Preserve existing user-visible behavior and data contracts unless the owner
  approves the change.
- Do not silently use mock data, fallback data, or invented defaults.
- Confirm the feature implementation goal with the user before coding; if the
  goal is missing or vague, ask the user to define it.
- Keep feature behavior in feature specs and update the matching spec for
  workflow, UI, backend, data, contract, or deployment changes.
- Do not mark work done or verified until tests, browser proof, logs, or a
  reproducible command proves the feature goal and end result are met.
- Use browser automation and screenshot proof for UI behavior changes when
  practical.
- Keep tenant, credential, privacy, and data-safety boundaries explicit.
- Never reset, truncate, migrate, or mutate production-like data without
  explicit approval and scoped proof.
- Ask before selecting or switching reviewers.
- Do not push or release until the selected review is complete or the user
  explicitly overrides the review rule.

## Do Not Lose

These compact reminders protect high-risk behavior in every bootstrapped
project.

- Before touching a feature, read `docs/goal/features/index.md`, then read the
  matching `docs/goal/features/<feature-slug>/feature.md`.
- Preserve checked or verified behavior in feature specs unless the user
  approves a change.
- Keep environment, tenant, deployment, and credential assumptions explicit.
- Keep related apps or repositories separate unless the user asks for
  cross-project work.
- Long-running actions should use an explicit submit-and-poll or equivalent job
  contract and preserve old terminal result shapes.
- If a selected reviewer is unavailable, report that and ask before fallback.
- Review prompts must say read-only, no edits, findings first with file/line
  refs, and review both `docs/goal/goal.md` and relevant feature specs.

## Workflow

Always read:

- `docs/goal/bugs.md`

Task-mode required guides:

- Implementation/coding:
  - `../feat-implement-docs/how-to/how to instruct LLM/ai-coding-rules.md`
  - `../feat-implement-docs/how-to/how to instruct LLM/ai-coding-safety.md`
  - `../feat-implement-docs/how-to/how to instruct LLM/ai-coding-structure.md`
- Review:
  - `../feat-implement-docs/how-to/how to instruct LLM/ai-review.md`
- Design/architecture:
  - `../feat-implement-docs/how-to/how to instruct LLM/ai-architect.md`
- Test/test-plan/QA:
  - `../feat-implement-docs/how-to/how to instruct LLM/ai-testing.md`

When a request spans multiple modes, read every matching guide before acting.
Examples:

- Design then implementation: read `ai-architect.md`, then the coding guides.
- Implementation with tests: read the coding guides and `ai-testing.md`.
- Review of implemented work: read `ai-review.md`.

Legacy guide aliases:

- `../feat-implement-docs/how-to/how to instruct LLM/ai-coding-rules.md`
- `../feat-implement-docs/how-to/how to instruct LLM/ai-coding-safety.md`
- `../feat-implement-docs/how-to/how to instruct LLM/ai-coding-structure.md`
- `../feat-implement-docs/how-to/how to instruct LLM/ai-testing.md`
- `../feat-implement-docs/how-to/how to instruct LLM/ai-review.md`

Read when relevant:

- UI/frontend/admin:
  `../feat-implement-docs/how-to/how to instruct LLM/ai-coding-ui.md`
- Implementation stage:
  `../feat-implement-docs/how-to/how to instruct LLM/ai-implemation-stage.md`
- The misspelled `ai-implemation-stage.md` filename is intentional until the
  source file is renamed.

Start rules:

- Follow the user request when instructions conflict, or ask.
- Confirm the feature implementation goal in plain language before coding.
- If the goal is missing, vague, or implied, ask the user to define or approve
  it.
- Clarify only missing user goal, UI/backend behavior, real values,
  credentials, files, output, or success proof.
- Use `bugs.md` first for repeated issues and update it when a repeated mistake
  appears.
- Before init/delegation, ask which agent to init: `self`, `codex`, or
  `claude`.

## Specs And Plans

Feature specs:

- Live at `docs/goal/features/<feature-slug>/feature.md`.
- Must state the feature implementation goal.
- Must be updated for workflow, UI, backend, data, contract, schema,
  deployment, access, or persistence changes.
- If no spec fits, create one and add it to `docs/goal/features/index.md`.
- Do not mark `verified` or check a box without passing proof.

Allowed status values for new or edited specs:

- `not-started`
- `partial`
- `implemented-unverified`
- `verified`
- `blocked`

Implementation plans:

- Required for multi-step or risky work.
- Store plan files in the project planning docs location.
- Prefer
  `../feat-implement-docs/<YYYY-MM-DD>-<feature-slug>/<YYYY-MM-DD>-<feature-slug>.md`.
- For narrow bug fixes that preserve the existing contract, a final-answer note
  is enough unless the bug reveals a missing feature rule.

Spec-only requests:

- Update or create the spec.
- Document the next workflow.
- Do not implement unless the user asks.
- Use Codex critique when available; otherwise do a labeled self-review.
- Critique must use `ai-review.md`.

## Engineering

Boundary:

- Active project: `DocEX`.
- Related projects: `workspace sibling repos under /Users/maoyi/llamasee`.
- Do not copy or edit unrelated repositories unless asked.
- Read related repositories only when needed to verify integration behavior,
  deployment, routing, or shared contracts.

Correctness:

- Review old behavior before and after code changes.
- Preserve fields, names, columns, actions, downloads, views, persisted data,
  visible details, and stable contracts unless the user approves otherwise.
- Do not finish only because code changed.
- Before claiming completion, compare the result against the feature goal or
  user-requested end state.
- Verify the actual end result with a test, browser proof, screenshot, API
  check, log, or reproducible command.
- If verification cannot run, say why and mark the work partial.
- Add tests for every completed workflow claim.

Data and files:

- Do not add tables, columns, template renames, public API field changes, or
  persisted-key changes without approval.
- Prefer existing adapters, registries, bindings, and config stores.
- Put workflow proof under `tests/`, not ad hoc scripts.
- Gate live or mutating tests with explicit flags such as `--live`.
- Do not add loose "maybe useful" scripts.
- Operational tools need a clear owner and purpose.

Configuration:

- Versioned configuration owns product and tenant defaults.
- Runtime storage owns mutable state, user edits, generated outputs, and audit
  events.
- Track hardcoded behavior that should become configuration in
  `docs/goal/configuration-pending.md`.

Visibility:

- Track hidden, disabled, deprecated, or preserved UI/API elements in
  `docs/goal/visibility-decisions.md`.
- Hidden means unavailable or not visible in that surface.
- Hidden does not mean deleted from APIs, data models, or stored data unless a
  feature spec says so.
- Do not remove a hidden item unless the owner asks to show or restore it.

## Review And Handoff

Review:

- Ask the user which reviewer to start: `codex`, `claude`, or `self`.
- Record `Reviewer selected: <choice>`.
- Do not silently switch reviewers.
- Reviews must be read-only.
- External reviews must use `ai-review.md`.
- Reviewers must flag missing or unconfirmed feature implementation goals.
- Reviewers must flag completion claims without proof that the goal or requested
  end state was met.

Before release or handoff:

- Update feature spec status and verification proof.
- Update `bugs.md` for reusable debugging lessons.
- Create a handoff note when work is incomplete, risky, or likely to continue
  elsewhere.

## Verification

Default command:

```bash
pytest
```

UI proof command, when applicable:

```bash
npm run test:e2e or browser smoke test
```

Live proof must:

- Open the real UI/API/job path.
- Exercise the user workflow.
- Verify the feature goal/end state.
- Verify generated files, API status, logs, objects, persisted records, or UI
  state as relevant.
- Explain any skipped proof and mark the work partial.

After editing this file:

```bash
git diff --check -- docs/goal/goal.md
```

## Feature Index

Feature index lives at `docs/goal/features/index.md`.

No unindexed open items remain. Add new items only after updating the relevant
feature spec and index.
