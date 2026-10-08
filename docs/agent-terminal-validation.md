# Agent terminal validation

## Purpose

Kneekura WhiteNyankocats has a growing set of Python, PowerShell, Android SDK,
ADB and signing workflows. Several real failures have occurred at the terminal
boundary even when the underlying design was sound. This layer gives coding
agents a repeatable place to execute and observe commands before a human is
asked to run them.

The goal is not a fake terminal. The goal is a small, auditable execution
contract:

`agent -> isolated/repository validation -> evidence -> user gate (only if required)`

## Components

- `tools/agent_terminal/verify.py`
  - executes argv directly with `shell=False`;
  - records executable resolution, cwd, stdout, stderr, exit code and timeout;
  - emits JSON evidence under `.agent-validation/reports/`;
  - supports a single command, a committed plan and a self-test;
  - can redact values sourced from named environment variables.
- `tools/agent_terminal/check_powershell_syntax.ps1`
  - statically parses the repository's PowerShell scripts using PowerShell's
    own parser;
  - converts parser errors into a failing exit code.
- `.agent-validation/plan.json`
  - reviewable list of commands that an agent/CI may execute;
  - avoids a remotely supplied arbitrary shell command input.
- `.github/workflows/agent-terminal-validation.yml`
  - runs the harness on both Ubuntu and Windows;
  - uploads JSON reports even after failure;
  - uses read-only repository permissions and no secrets.
- `AGENTS.md`
  - makes validation-before-handoff part of the coding-agent contract.

## Local use

Self-test the harness:

```text
python -m tools.agent_terminal.verify self-test
```

Run the repository plan:

```text
python -m tools.agent_terminal.verify plan .agent-validation/plan.json
```

Validate a specific argv command:

```text
python -m tools.agent_terminal.verify run \
  --name phase-c-preflight-help \
  -- python -m tools.base_mod.phase_c_preflight --help
```

A successful invocation prints `AGENT_TERMINAL_VERDICT=PASS`. The JSON report
contains the evidence used for that verdict.

## User-gate boundary

Some important Phase C commands cannot be fully reproduced in GitHub Actions:

- an authorized physical Android device;
- the owner-only Battle Cats export;
- the local signing keystore/password;
- already-downloaded app-private/external game data.

Those are not CI failures. They are `USER_GATE` dependencies. The agent should
first run unit tests, static PowerShell parsing, CLI/preflight checks and any
other non-secret work it can perform. Only the smallest remaining device step
should then be handed to the user.

This distinction prevents two bad outcomes: claiming a device test that never
happened, and making the user discover ordinary syntax/path/import errors that
CI could have caught first.

## Security boundary

The workflow intentionally does **not** accept a `command` text input from
`workflow_dispatch`. Arbitrary remote command strings make quoting harder to
reason about and turn the validator into a generic remote shell. Commands are
committed as argv arrays in `.agent-validation/plan.json`, so they are visible
in Git history and PR review.

Secrets should be supplied only at the final local/device boundary. If a local
validation command inherits a secret environment variable and may print it,
use `--secret-env NAME`; the harness replaces the exact value in argv/stdout/
stderr before writing the report.

## Promotion rule

A command is suitable for human handoff when:

1. repository-local/static validation is PASS;
2. required platform-specific checks are PASS;
3. any remaining unavailable dependency is explicitly classified as
   `USER_GATE`;
4. the command has not already failed unchanged in the current debugging loop.

For recurring failures, add the root cause and regression rule to
`docs/research/failure-repair-history.md`.
