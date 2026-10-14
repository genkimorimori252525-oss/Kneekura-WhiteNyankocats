---
name: continuity-guard
description: Codex Continuity Guard - Manage long-term goals, checkpointing, restoration, and audits across context compactions and sessions.
---

# Continuity Guard Skill

This skill allows Codex to maintain project charter continuity, create checkpoints, perform integrity audits, and recover state.

<!-- CCG_SKILL_START -->

Run commands through the installed CLI:

`py -3.10 "C:\Users\genki\.codex\tools\continuity-guard\continuity.py" <command>`

Run project commands from the target project's root directory. Initialize multi-step work without changing Hook configuration with `init --no-hooks`.
For a new project, pass the user's stated goal with `--mission` and only explicitly stated constraints with `--constraints`.

## Available Actions

- Check project status:
  `py -3.10 "C:\Users\genki\.codex\tools\continuity-guard\continuity.py" status`
- Initialize continuity files for a multi-step project:
  `py -3.10 "C:\Users\genki\.codex\tools\continuity-guard\continuity.py" init --no-hooks --mission "<USER_STATED_GOAL>" [--constraints "<USER_STATED_CONSTRAINTS>"]`
- Create a checkpoint with test evidence:
  `py -3.10 "C:\Users\genki\.codex\tools\continuity-guard\continuity.py" checkpoint --task <TASK_ID> --agent <AGENT_NAME>`
- Run integrity audit:
  `py -3.10 "C:\Users\genki\.codex\tools\continuity-guard\continuity.py" audit`
- View restoration context:
  `py -3.10 "C:\Users\genki\.codex\tools\continuity-guard\continuity.py" restore --brief`
- Diagnose environment:
  `py -3.10 "C:\Users\genki\.codex\tools\continuity-guard\continuity.py" doctor`
- Remove CCG-managed project instructions and Skill:
  `py -3.10 "C:\Users\genki\.codex\tools\continuity-guard\continuity.py" rollback`

<!-- CCG_SKILL_END -->
