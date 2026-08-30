# Migration

This kit is designed to be copied into the repository root.

## What it replaces/adds

Copy:

- `AGENTS.md` (replaces the current long canonical agent policy)
- `GEMINI.md`
- `README-agent-kit.md`
- `.agents/`
- `.codex/`
- `.gemini/`

Keep the rest of the NES Pascal repository unchanged.

## Recommended migration

1. Create a branch dedicated to the agent-kit migration.
2. Save the previous `AGENTS.md` in Git history; no repository backup file is necessary.
3. Copy this kit into the repository root.
4. Review `.codex/config.toml` model names against the Codex version installed locally.
5. Ask Codex and Gemini to read `AGENTS.md` and list the available roles/skills without modifying code.
6. Run a small bounded task using `ze_da_oficina`.
7. Confirm specialists remain read-only and that normal work does not spawn them automatically.
8. Commit the migration separately from compiler feature work.

## Intentional changes from the old AGENTS.md

Detailed repeatable workflows were moved into skills so ordinary tasks do not need to reason over every procedure.

The canonical file keeps stable rules and routing decisions.

No language feature or roadmap behavior should be changed by this migration.
