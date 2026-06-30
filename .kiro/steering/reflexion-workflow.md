---
inclusion: manual
description: Full reflexion workflow loop — self-improving docs-update process. Pull in with #reflexion-workflow when needed.
---

# Reflexion Workflow

## Loop

```
Request → Consult Docs → Code → Test → Fix → Reflect → Update Docs
              ↑                                              |
              └──────────────────────────────────────────────┘
```

## Steps

1. **Understand** — Identify needed endpoints. Check `#[[file:docs/api-overview.md]]` and the endpoint routing table in `ncm-api-development` steering.
2. **Check known issues** — Read `#[[file:docs/known-issues.md]]` to avoid known pitfalls.
3. **Write code** — Follow `#[[file:docs/common-patterns.md]]`. Use NCM SDK when possible. Include error handling and retries.
4. **Test** — Run code. Check for syntax, import, and runtime errors. Verify output.
5. **Fix** — Diagnose and fix errors iteratively. Note any doc gaps found.
6. **Reflect and update** — See below.

## When to Update Docs

**Update if:**
- Discovered undocumented API behavior
- Found a documentation error
- Created a reusable pattern
- Hit a gotcha others should know about

**Skip if:**
- Discovery is app-specific
- User-specific config issue
- Already documented

## What to Update

| Discovery | Target File |
|-----------|-------------|
| New gotcha | `docs/known-issues.md` → "Discovered Issues Log" |
| Reusable pattern | `docs/common-patterns.md` |
| Doc error/addition | Relevant `docs/*.md` file |
| New endpoint routing | `.kiro/steering/ncm-api-development.md` |
| Any change | Log in `docs/CHANGELOG.md` |

## Formats

`known-issues.md`: `### [Title] (discovered YYYY-MM-DD)` + description/workaround

`CHANGELOG.md`: `## YYYY-MM-DD — [Description]` + bullet list of changes
