---
inclusion: auto
---

# Reflexion Workflow System

## Purpose

This steering file defines the reflexion loop: a self-improving workflow where the AI
updates its own documentation and steering rules when it discovers new information
during development.

## The Reflexion Loop

```
User Request → Consult Docs → Build Code → Test → Fix Errors → Reflect → Update Docs
                  ↑                                                          |
                  └──────────────────────────────────────────────────────────┘
```

## When Building Any NCM Application

### Step 1: Understand the Request
- Identify which API endpoints are needed
- Check `#[[file:docs/api-overview.md]]` for API basics
- Use the Endpoint Routing Guide in the NCM steering to find the right docs

### Step 2: Check Known Issues
- Read `#[[file:docs/known-issues.md]]` before writing code
- Avoid known pitfalls

### Step 3: Write Code
- Follow patterns from `#[[file:docs/common-patterns.md]]`
- Use the NCM SDK when possible
- Include proper error handling and retry logic

### Step 4: Test
- Run the code
- Check for syntax errors, import errors, runtime errors
- Verify output matches expectations

### Step 5: Fix Errors
- If errors occur, diagnose and fix
- Re-run until clean
- If the error reveals a documentation gap, note it for Step 6

### Step 6: Reflect and Update
After completing the task, ask yourself:

**Should I update documentation?** Update if:
- You discovered an API behavior not documented in `docs/`
- You found a documentation error
- You created a reusable pattern others could benefit from
- You hit a gotcha that should be warned about

**Should I NOT update documentation?** Skip if:
- The discovery is specific to this one application
- It's a user-specific configuration issue
- It's already documented

**What to update:**
- `docs/known-issues.md` — append new gotchas under "Discovered Issues Log"
- `docs/common-patterns.md` — add new reusable patterns
- `docs/CHANGELOG.md` — log what changed and why
- Relevant `docs/*.md` file — fix errors or add missing info
- `.kiro/steering/*.md` — update routing guide if new endpoint patterns discovered

## Documentation Update Format

When appending to `docs/known-issues.md`:
```markdown
### [Short Title] (discovered YYYY-MM-DD)
[Description of the issue and workaround]
```

When appending to `docs/CHANGELOG.md`:
```markdown
## YYYY-MM-DD — [Brief Description]
- [What changed and why]
```

## Quality Gates

Before considering any NCM application complete:
1. Code runs without errors
2. All API calls use proper authentication
3. All URLs have trailing slashes
4. Pagination is handled for list operations
5. Error handling with retries is implemented
6. No deprecated endpoints are used
7. Documentation has been updated if applicable
