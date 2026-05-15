# Test Cases

Human-readable catalogue of every scenario worth covering. One file per top-level feature bucket, mirroring `Features.md`'s section numbering. This is the scope contract between product features and tests.

## Format

Each case is one line:

```
<STATUS> <ID>: <GIVEN context,> WHEN <action>, THEN <expected result>
```

## Status Markers

| Marker | Meaning |
|--------|---------|
| ❌ | Not yet covered by a test |
| ✅ | Covered and passing |
| 🟡 | Partially covered |
| 🧪 | Test exists but flaky or not yet merged |
| 🚫 | Consciously out of scope (add a brief reason inline) |

## ID Format

`<BUCKET>-<SECTION>-<NN>` — e.g. `AUTH-1.2-03`

Bucket prefix matches the file name (e.g. `01-auth.md` → `AUTH`).

## Rules

- Never renumber existing IDs. If a case is deleted, leave its number unused — new cases continue past it.
- Flip the status marker in the same commit as the test that covers the case.
- Cross-reference test names with case IDs (`it('AUTH-1.2-03: ...')`) so grep finds both directions.
- Prose only — no test code in this folder.
