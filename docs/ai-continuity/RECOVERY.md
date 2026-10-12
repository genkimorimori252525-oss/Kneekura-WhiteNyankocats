# Recovery and Rollback Procedures

## If Hooks Fail to Fire
1. Use the `continuity-guard` Skill to run `restore --brief` manually.
2. If using a project-local installation, run `python tools/continuity-guard/continuity.py restore --brief`.
3. Verify `.codex/hooks.json` configuration and trust status in Codex.

## If Charter Drift is Detected
1. Use the `continuity-guard` Skill to run `audit` and identify changes.
2. Check `docs/ai-continuity/AMENDMENTS/` for approved updates.
3. If legitimate, update `approved_sha256` in `PROJECT_CHARTER.md`.

## Rollback
1. Use the `continuity-guard` Skill to run `rollback` and remove CCG integration cleanly.
2. If using a project-local installation, run `python tools/continuity-guard/continuity.py rollback`.
