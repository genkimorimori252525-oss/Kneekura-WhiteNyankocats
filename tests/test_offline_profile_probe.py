from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "base_mod" / "run_offline_profile_probe.ps1"


def test_offline_profile_probe_is_read_only():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "adb_push_used = $false" in text
    assert "mutation_attempted = $false" in text
    assert " pull " in text
    assert "Get-FileHash -Algorithm SHA256" in text
    assert "Copy-Item" in text
    assert "SAVE_DATA" in text
    assert "BACKUP_SAVE_DATA" in text

    forbidden = (
        " adb push ",
        " uninstall ",
        " pm clear ",
        " shell rm ",
        " shell mv ",
        " shell cp ",
        " install-multiple ",
        " install -r ",
    )
    lowered = " " + " ".join(text.lower().split()) + " "
    for token in forbidden:
        assert token not in lowered, token


def test_offline_profile_probe_uses_research_package_by_default():
    text = SCRIPT.read_text(encoding="utf-8")
    assert '[string]$Package = "jp.kn.trace.battlecats"' in text
    assert "/Android/data/$Package/files" in text


def test_offline_profile_probe_creates_independent_rollback_copy():
    text = SCRIPT.read_text(encoding="utf-8")
    assert '".rollback"' in text
    assert "rollback_sha256" in text
    assert "Rollback copy hash mismatch" in text


def test_offline_profile_probe_runs_readonly_save_inspection():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "tools.base_mod.inspect_save_data" in text
    assert "SAVE_DATA-inspection.json" in text
    assert "save_inspection_generated" in text
