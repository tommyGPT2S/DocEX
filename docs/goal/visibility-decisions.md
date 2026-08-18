# Visibility Decisions

Canonical list of intentionally hidden, disabled, deprecated, or preserved
surface elements.

Read this when the user asks:

- What is hidden?
- What did we hide?
- Why is this control disabled?
- Which old fields must stay visible?
- Similar questions about visible or intentionally unavailable behavior.

## Rules

- Keep each item short.
- Include the surface, item, decision, reason, owner, and date when known.
- Hidden does not mean deleted from APIs, data models, or stored data.
- Disabled does not mean unsupported unless the feature spec says so.
- Deprecated does not mean removable without an explicit migration plan.
- Add new items when the owner asks to hide, disable, restore, or preserve more.
- Do not remove an item unless the owner asks to restore or fully delete it.

## Active Decisions

| Surface | Item | Decision | Reason | Owner | Date |
| --- | --- | --- | --- | --- | --- |
| `<screen/api>` | `<item>` | `<hidden/disabled/preserved/deprecated>` | `<why>` | `<owner>` | `<YYYY-MM-DD>` |

## Restored Or Removed Decisions

| Surface | Item | Previous Decision | New Decision | Proof | Date |
| --- | --- | --- | --- | --- | --- |
| `<screen/api>` | `<item>` | `<hidden>` | `<restored>` | `<test, screenshot, or PR>` | `<YYYY-MM-DD>` |
