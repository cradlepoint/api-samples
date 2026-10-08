# CLAUDE.md

Instructions for AI coding agents working in this repo.

**There is deliberately no `AGENTS.md`.** Kiro auto-loads a root `AGENTS.md` into
every request as always-on context, where it duplicated
`.kiro/steering/project-setup.md` (already `inclusion: always`) and doubled the
standing token cost. Earlier versions also inlined all six steering files in full and
drifted out of sync. Do not recreate it. Kiro reads `.kiro/steering/`; this file
serves the agents that don't.

**The detailed rules live in `.kiro/steering/*.md`** — plain markdown, read them
directly:

| Read this file | When |
|---|---|
| `.kiro/steering/project-setup.md` | Always — venv, credentials, setup, web apps |
| `.kiro/steering/code-standards.md` | Touching `scripts/**/*.py` |
| `.kiro/steering/ncm-api-development.md` | Touching Python in `scripts/`, `ncm/`, `ncm2/`, `web_apps/` |
| `.kiro/steering/web-ui-standards.md` | Touching `*.html`, `*.css`, or `web_apps/**` |
| `.kiro/steering/setup-environment.md` | User asks to set up / install deps / fix imports, or `.venv/` is missing |
| `.kiro/steering/reflexion-workflow.md` | Finishing a task, or asked for the full docs loop |

Fix rules at the source — in the steering file that owns them, not here.

## The essentials

Enough to avoid the three mistakes that cost the most time. Full detail in
`project-setup.md`.

1. **Always use the venv at `.venv/`, never system Python.** Prefer activating it and
   calling `python3` (`python` on Windows), chained into one command since activation
   does not persist between tool calls:

   ```bash
   source .venv/bin/activate && python3 scripts/get.py       # macOS / Linux
   .venv\Scripts\Activate.ps1; python scripts\get.py         # Windows PowerShell
   ```

   `.venv/bin/python` / `.venv\Scripts\python.exe` is the fallback. Detect the
   platform; do not hardcode `.venv/bin`.

2. **Never run bare `setup_env.py` from a tool call — it hangs until timeout.** Tool
   calls get a tty, so it prompts for credentials with no human attached and no
   visible prompt. Use `setup_env.py --skip-credentials`. If `.venv/` is missing, run
   that immediately rather than asking or failing the request.

3. **Credentials never enter the transcript.** They live in `.env`
   (`X_CP_API_ID`, `X_CP_API_KEY`, `X_ECM_API_ID`, `X_ECM_API_KEY`, and
   `NCM_API_TOKEN` for v3). Never ask the user to paste keys into chat — send them to
   `setup_env.py --credentials-only`, where input is hidden. Never print, log, or
   commit credential values.

## Automation rules

`.kiro/hooks/` automates these for Kiro. Agents without a hook system should run them
at the described moment.

1. **At session start** — run `python3 scripts/utils/env_status.py` (`python` on
   Windows) to report venv, dependency and credential state. This is the one script
   that runs under the system launcher: it is stdlib-only by design so it can report
   on a venv that does not exist yet. If it says `venv: MISSING`, set up the
   environment before anything else.

2. **After running Python** — if the output contains errors (syntax, import, runtime,
   or API), diagnose and fix, then re-run until clean. Do not report a task complete
   on top of a failing run. If the error reveals undocumented API behavior, note it
   for the reflexion step.

3. **Before finishing** — if you discovered an API behavior, gotcha, or reusable
   pattern that is generally applicable and not already in `docs/known-issues.md` or
   `docs/common-patterns.md`, update the relevant doc and append to
   `docs/CHANGELOG.md`. Otherwise do nothing. Formats and targets are in
   `reflexion-workflow.md`.
