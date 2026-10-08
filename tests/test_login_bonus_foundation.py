import unittest

from tools.analyze_login_bonus_foundation import (
    group_rewards,
    item_index_names,
    parse_login_groups,
)


class LoginBonusFoundationTests(unittest.TestCase):
    def test_parse_login_groups_matches_bcc_variable_group_shape(self) -> None:
        row = [
            949, 901, 255, 0, 0, 19, 0,
            2, 21, 0, 21, 1, 0, 20, 3,
            1, 20, 0, 20, 3,
        ]
        header, groups = parse_login_groups(row)
        self.assertEqual(header, [949, 901, 255, 0, 0, 19, 0])
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0], [2, 21, 0, 21, 1, 0, 20, 3])
        self.assertEqual(groups[1], [1, 20, 0, 20, 3])

    def test_reward_group_preserves_kind_item_index_amount(self) -> None:
        parsed = group_rewards([2, 21, 0, 21, 1, 0, 20, 3])[0]
        self.assertEqual(parsed["group_value"], 21)
        self.assertEqual(
            parsed["rewards"],
            [
                {"kind": 0, "item_index": 21, "amount": 1},
                {"kind": 0, "item_index": 20, "amount": 3},
            ],
        )

    def test_gatya_item_names_are_indexed_after_header(self) -> None:
        payload = (
            "Rarity,reflectORstorage,Price,stageDropItemID,quantity,SeverID,"
            "category,index,srcItemID,mainMenuType,gatyaTicketID,imgID,comment\n"
            "0,0,1,6,1,201,0,0,-1,1,-1,-1,ＸＰ\n"
            "1,0,1000,11,1,202,0,0,-1,3,-1,-1,にゃんこチケット\n"
            "3,0,1000,12,1,203,0,0,-1,4,-1,-1,レアチケット\n"
        ).encode()
        names = item_index_names(payload)
        self.assertEqual(names[0], "ＸＰ")
        self.assertEqual(names[1], "にゃんこチケット")
        self.assertEqual(names[2], "レアチケット")


if __name__ == "__main__":
    unittest.main()
