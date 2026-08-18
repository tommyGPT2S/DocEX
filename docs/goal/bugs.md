# Fixed Bugs

Use this file as durable memory for repeated bugs, regressions, and debugging
rules.

Read this before debugging or changing related code.

## Rules

- Add an entry when a bug is fixed and likely to recur.
- Keep each entry factual.
- Include symptoms, root cause, fix, validation, and prevention.
- Prefer commands that another developer can rerun.
- Do not include secrets.
- Do not include private customer data.
- Keep project-specific paths exact when this file is used inside a project.

## Entry Template

### <Bug Title>

**Date:** `<YYYY-MM-DD>`

**Symptoms:**

- `<What the user, logs, tests, or system showed.>`

**Root cause:**

- `<The actual cause, not only the surface error.>`

**Fix:**

- `<What changed.>`

**Validation:**

```bash
<command>
```

Result: `<passed / failed / partial, with important evidence>`.

**Prevention / Debugging Rule:**

- `<What to check first next time.>`
- `<What not to assume.>`
