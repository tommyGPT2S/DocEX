# Goal Documentation Framework

Use this folder as a reusable framework for project goal docs.

Copy the files into a project as `docs/goal/`, then replace placeholders such as
`DocEX`, `<feature-slug>`, and `<command>`.

## Files

- `goal.md`: root contract for agent workflow, project rules, planning,
  verification, review, and handoff expectations.
- `bugs.md`: durable memory for repeated bugs, regressions, and debugging rules.
- `configuration-pending.md`: tracker for behavior that should move from code or
  runtime state into versioned configuration.
- `visibility-decisions.md`: tracker for UI or API elements intentionally
  hidden, disabled, deprecated, or kept visible.
- `features/index.md`: feature-spec index. Agents read this before choosing a
  feature spec.
- `features/_template/feature.md`: template for detailed feature specs.
- `handoffs/_template.md`: template for passing context into another chat,
  developer, or agent.

## Recommended Project Layout

```text
docs/goal/
  goal.md
  bugs.md
  configuration-pending.md
  visibility-decisions.md
  features/
    index.md
    <feature-slug>/
      feature.md
  handoffs/
    <YYYY-MM-DD>-<feature-slug>.md
```

Keep the root file small. Put the feature list in `features/index.md`. Put
feature behavior in feature specs. Put historical debugging lessons in
`bugs.md`. Put UI visibility choices in `visibility-decisions.md`. Put
transition context in handoffs.
