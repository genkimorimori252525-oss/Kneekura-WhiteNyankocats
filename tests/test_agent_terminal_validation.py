from pathlib import Path
import os
import sys
import tempfile
import unittest

from tools.agent_terminal.verify import run_command


ROOT = Path(__file__).resolve().parents[1]


class AgentTerminalValidationTests(unittest.TestCase):
    def test_runner_captures_success_and_nonzero_exit(self) -> None:
        success = run_command(
            [sys.executable, "-c", "print('ok')"],
            name="success",
            cwd=ROOT,
            timeout_seconds=10,
        )
        self.assertEqual(success.status, "PASS")
        self.assertEqual(success.exit_code, 0)
        self.assertIn("ok", success.stdout)

        failure = run_command(
            [sys.executable, "-c", "import sys; print('bad', file=sys.stderr); sys.exit(9)"],
            name="failure",
            cwd=ROOT,
            timeout_seconds=10,
        )
        self.assertEqual(failure.status, "FAIL")
        self.assertEqual(failure.exit_code, 9)
        self.assertIn("bad", failure.stderr)

    def test_runner_fails_closed_for_missing_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            result = run_command(
                ["definitely-not-a-real-kneekura-command"],
                name="missing",
                cwd=Path(temp_name),
                timeout_seconds=5,
            )
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.exit_code, 127)
        self.assertIn("executable not found", result.stderr)


    def test_secret_environment_value_is_redacted(self) -> None:
        key = "KNEEKURA_AGENT_TERMINAL_TEST_SECRET"
        old = os.environ.get(key)
        os.environ[key] = "agent-terminal-super-secret"
        try:
            result = run_command(
                [sys.executable, "-c", f"import os; print(os.environ[{key!r}])"],
                name="redaction",
                cwd=ROOT,
                timeout_seconds=10,
                secret_env=[key],
            )
        finally:
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
        self.assertEqual(result.status, "PASS")
        self.assertIn("<redacted>", result.stdout)
        self.assertNotIn("agent-terminal-super-secret", result.stdout)

    def test_agent_contract_requires_validation_before_handoff(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Validate before handoff", text)
        self.assertIn("USER_GATE", text)
        self.assertIn("--secret-env", text)

    def test_workflow_covers_windows_and_has_no_remote_command_input(self) -> None:
        text = (
            ROOT / ".github/workflows/agent-terminal-validation.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("windows-latest", text)
        self.assertIn("ubuntu-latest", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("inputs.command", text)
        self.assertNotIn("${{ inputs.command }}", text)


if __name__ == "__main__":
    unittest.main()
