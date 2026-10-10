import json
import unittest

from tools.base_mod.audit_local_offline_ui_corpus import (
    UI_KEYS, DATALOCAL_NAMES, summarize_corpus,
)


def sample():
    values = "\n".join(key + "\tmessage_" + key for key in UI_KEYS).encode()
    display = json.dumps({"MapSet":{"1":{},"2":{}}}).encode()
    gacha = b"GatyaSetID\tBannerON_OFF\n1\t1\n2\t1\n"
    files = {name: name not in ("event.json", "gatya.tsv")
             for name in DATALOCAL_NAMES}
    return values, display, gacha, files


class LocalUICorpusAuditTests(unittest.TestCase):
    def test_distinct_stop_messages_and_bundled_data_only(self):
        result = summarize_corpus(*sample())
        self.assertTrue(result["ui_categories_are_distinct"])
        self.assertEqual(result["local_event_display_mapset_count"], 2)
        self.assertEqual(result["local_gacha_option_rows_excluding_header"], 2)
        self.assertFalse(result["data_local_file_present"]["gatya.tsv"])
        self.assertFalse(result["data_local_file_present"]["event.json"])
        self.assertEqual(result["original_native_decision_origin"], "NOT_TRACED")
        self.assertEqual(result["specific_user_save_restriction_cause"], "NOT_DETERMINED")

    def test_bad_keys_event_or_gacha_fail_closed(self):
        payload, event, gacha, files = sample()
        with self.assertRaises(ValueError):
            summarize_corpus(payload + b"\ngamestop\tdouble", event, gacha, files)
        with self.assertRaises(ValueError):
            summarize_corpus(payload, b"{}", gacha, files)
        with self.assertRaises(ValueError):
            summarize_corpus(payload, event, b"fake-header\n", files)
        files["eventDisplayData.json"] = False
        with self.assertRaises(ValueError):
            summarize_corpus(payload, event, gacha, files)


if __name__ == "__main__":
    unittest.main()
