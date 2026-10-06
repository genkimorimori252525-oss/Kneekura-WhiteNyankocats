import json

import pytest

from tools.base_mod.build_offline_profile_unit_manifest import (
    apply_asset_audit_gate,
    parse_unit_selection,
)


def _csv(rows):
    return ("\n".join(",".join(str(v) for v in row) for row in rows) + "\n").encode()


def _buy(*, position=0, rarity=4, version=150700, tf=0, uf=0):
    row = ["0"] * 63
    row[13] = str(rarity)
    row[14] = str(position)
    row[17] = str(rarity)
    row[21] = "10"
    row[23] = str(tf)
    row[24] = str(uf)
    row[49] = "30"
    row[50] = "50"
    row[51] = "20"
    row[57] = str(version)
    row[58] = "50"
    row[61] = "-1"
    row[62] = "-1"
    return row


def _book(*, visible=1, total_forms=3, limited=0):
    row = ["0"] * 8
    row[0] = str(visible)
    row[1] = str(limited)
    row[2] = str(total_forms)
    row[3] = "0"
    return row


def test_selection_requires_guide_visible_and_playable():
    manifest = parse_unit_selection(
        unitbuy_payload=_csv([
            _buy(position=0),
            _buy(position=1),
            _buy(position=-1),
        ]),
        picturebook_payload=_csv([
            _book(visible=1),
            _book(visible=0),
            _book(visible=1),
        ]),
    )

    assert [item["asset_id"] for item in manifest["eligible_units"]] == [0]
    excluded = {item["asset_id"]: item["excluded_reasons"] for item in manifest["excluded_units"]}
    assert excluded[1] == ["catguide_hidden"]
    assert excluded[2] == ["not_roster_playable"]


def test_first_form_contract_does_not_force_progression():
    manifest = parse_unit_selection(
        unitbuy_payload=_csv([_buy(position=0, tf=123, uf=456)]),
        picturebook_payload=_csv([_book(visible=1, total_forms=4)]),
    )
    state = manifest["eligible_units"][0]["bootstrap_state"]

    assert state["owned"] is True
    assert state["gacha_seen"] is True
    assert state["current_form"] == 0
    assert state["unlocked_forms"] == 0
    assert state["force_true_form"] is False
    assert state["force_fourth_form"] is False
    assert state["force_talents"] is False
    assert state["force_upgrade_level"] is False


def test_units_after_anchor_are_excluded():
    manifest = parse_unit_selection(
        unitbuy_payload=_csv([_buy(position=0, version=150800)]),
        picturebook_payload=_csv([_book(visible=1)]),
    )
    assert manifest["eligible_units"] == []
    assert manifest["excluded_units"][0]["excluded_reasons"] == ["introduced_after_anchor"]


def test_asset_gate_fails_closed_on_eligible_incomplete_unit():
    manifest = parse_unit_selection(
        unitbuy_payload=_csv([_buy(position=0)]),
        picturebook_payload=_csv([_book(visible=1)]),
    )
    audit = {
        "source": {
            "export_sha256": "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
        },
        "result": {"unit_count": 882, "complete_unit_count": 881, "incomplete_unit_count": 1},
        "residuals": [{"asset_id": 0}],
    }

    with pytest.raises(ValueError, match="asset-incomplete"):
        apply_asset_audit_gate(manifest, audit)


def test_asset_gate_accepts_hidden_residual():
    manifest = parse_unit_selection(
        unitbuy_payload=_csv([
            _buy(position=0),
            _buy(position=1),
        ]),
        picturebook_payload=_csv([
            _book(visible=1),
            _book(visible=0),
        ]),
    )
    audit = {
        "source": {
            "export_sha256": "38c3bbb8d2cf2101793c9462617d4293e19fc99588b6655fd40299fd61a0ef56"
        },
        "result": {"unit_count": 882, "complete_unit_count": 881, "incomplete_unit_count": 1},
        "residuals": [{"asset_id": 1}],
    }

    apply_asset_audit_gate(manifest, audit)
    assert manifest["asset_gate"]["passed"] is True
    assert manifest["asset_gate"]["eligible_overlap"] == []
