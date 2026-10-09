# Agent terminal validation contract

This repository contains device-facing PowerShell and Android tooling where an
incorrect command can waste a long device/debug cycle. Coding agents must use
the repository validation harness before handing terminal commands to a human.

## Required behavior

1. **Validate before handoff.** For repository-local commands, run the command
   through `python -m tools.agent_terminal.verify run ... -- <argv>` or add it
   to `.agent-validation/plan.json` and run the plan.
2. **Use argv, not a shell string, when possible.** The harness deliberately
   executes with `shell=False` so quoting errors are exposed instead of hidden.
3. **Treat exit code, stdout and stderr as evidence.** A failed command is not a
   candidate for user handoff. Diagnose it, repair it, and rerun validation.
4. **Do not fake unavailable dependencies.** A physical Android device, the
   owner-only Battle Cats export, a signing key/password, or another unavailable
   external dependency is a `USER_GATE`. Validate every static/repository-local
   part first, then make only the irreducible user gate explicit.
5. **Never put secrets in reports.** Prefer environment variables. When a
   command may echo a secret already held in an environment variable, pass
   `--secret-env NAME` to the harness. Do not commit passwords, tokens, APKs,
   decrypted game assets, or device saves.
6. **PowerShell changes require Windows parsing.** The validation workflow runs
   every `tools/base_mod/*.ps1` through the PowerShell parser on `windows-latest`.
7. **PASS is scoped.** A CI PASS proves the command/tooling in the validation
   environment. It does not claim that an Android device interaction happened.
8. **Preserve failure knowledge.** Repeated or design-relevant failures belong
   in `docs/research/failure-repair-history.md`, with a regression check where
   practical.

## P0 full-local product safety gate (2026-10-09)

- **Zero external egress is a release requirement, not a future feature flag.** A build with `android.permission.INTERNET`, original `super.newHttpRequest(...)` fallthrough, unvetted analytics/advertising SDK initializers or untested native transport must not be called complete offline.
- **No modified official SAVE_DATA as the local game's authority.** The redesigned game must own a separate versioned local schema and must not rely on original account/inquiry tokens, client/server legality flags or official-save checks.
- Run the read-only `tools/base_mod/audit_offline_egress.py` against owner source/artifacts. Its findings reflect capability, **not proof that data was sent or that a ban was server-enforced**. A static clean result does not replace first-run device egress/IPC testing.
- Any requirement to preserve original UI or native loader is subordinate to the hard offline contract. Where that contract fails, investigate independent local host rather than bypassing a restriction dialog or reconnecting edited saves to official services.
- [Authoritative investigation/architecture reset](docs/architecture/2026-10-09-complete-local-offline-audit.md), [tracker issue #5](https://github.com/genkimorimori252525-oss/Kneekura-WhiteNyankocats/issues/5). No owner screenshot/account metadata in public GitHub.

## Standard commands

Harness self-test:

```text
python -m tools.agent_terminal.verify self-test
```

Run the committed repository plan:

```text
python -m tools.agent_terminal.verify plan .agent-validation/plan.json
```

Validate one command before presenting it to the user:

```text
python -m tools.agent_terminal.verify run --name example -- python -m tools.base_mod.phase_c_preflight --help
```

If a command cannot be executed because it needs a device or private material,
report it as `USER_GATE` rather than `PASS` or an invented successful result.
