"""Policy tests do not need an owner save or the private reference parser."""
import copy
from types import SimpleNamespace as N
import unittest

from tools.base_mod.pc_initial_profile import apply_policy, verify_unchanged, pristine_events


def profile():
    cats = [N(id=i, unlocked=0, gatya_seen=0, upgrade=N(base=0, plus=0),
              max_upgrade_level=N(base=0, plus=0)) for i in range(882)]
    chapters = [N(progress=0, stages=[N(clear_times=0, treasure=0, itf_timed_score=0)
                                     for _ in range(51)]) for _ in range(10)]
    save = N(cats=N(cats=cats), story=N(chapters=chapters),
             tutorial_state=0, koreaSuperiorTreasureState=0, ui6=0, cleared_eoc_1=0,
             menu_unlocks=[0]*6, new_dialogs_2=[0]*17,
             battle_items=N(items=[N(amount=0) for _ in range(6)]),
             ototo=N(engineers=0, base_materials=N(materials=[N(amount=0) for _ in range(16)])),
             talent_orbs=N(orbs={}))
    for name, count in [('catfruit',29),('catseyes',6),('catamins',3),
                        ('lucky_tickets',55),('labyrinth_medals',4),('treasure_chests',42)]:
        setattr(save,name,[0]*count)
    return save


class PcInitialProfileTests(unittest.TestCase):
    def test_claim_or_completed_chapter_without_stage_progress_is_not_pristine(self):
        clean={'chapters':[], 'chapter_completion_count':[0], 'stages_reward_claimed':{}}
        self.assertTrue(pristine_events(clean))
        for key,value in [('chapter_completion_count',[1]),('stages_reward_claimed',{'3':[True]})]:
            changed=copy.deepcopy(clean)
            changed[key]=value
            self.assertFalse(pristine_events(changed))

    def test_exact_story_and_rewards_preserve_current_levels_and_native_hard_caps(self):
        save=profile()
        save.cats.cats[25].upgrade=N(base=12,plus=3)
        targets={25:dict(required_increment=30),288:dict(required_increment=40),
                 80:dict(required_increment=0)}
        apply_policy(save,{24,25,288,80},{130},targets,[3,8],lambda i,n:N(id=i,value=n))
        self.assertEqual([c.progress for c in save.story.chapters],[48,48,48,0,48,0,0,0,0,0])
        for ci,c in enumerate(save.story.chapters):
            self.assertEqual(sum(t.clear_times>0 for t in c.stages),48 if ci in (0,1,2,4) else 0)
            self.assertEqual(sum(t.treasure==3 for t in c.stages),48 if ci in (0,1,2,4) else 0)
        self.assertEqual((save.cats.cats[25].upgrade.base,save.cats.cats[25].upgrade.plus),(12,3))
        self.assertEqual([save.cats.cats[i].max_upgrade_level.base for i in (25,288,80)],[30,40,0])
        self.assertEqual(save.cats.cats[130].unlocked,0)
        self.assertEqual(save.cats.cats[24].unlocked,1)
        self.assertEqual(save.xp,99_999_999)
        self.assertEqual(save.catfruit,[998]*29)
        self.assertEqual(set(save.talent_orbs.orbs),{3,8})

    def test_existing_unlisted_progress_and_stage_reward_are_refused(self):
        for tamper in ('future','reward'):
            save=profile()
            if tamper=='future': save.story.chapters[5].stages[0].clear_times=1
            else: save.cats.cats[130].unlocked=1
            with self.assertRaisesRegex(ValueError,'PC_PROFILE_NOT_PRISTINE'):
                apply_policy(save,{25},{130},{},[],lambda i,n:N(id=i,value=n))

    def test_diff_gate_rejects_credential_levels_plus_and_unlisted_treasures(self):
        before={'inquiry_code':'own-private-test','cats':{'cats':[{'upgrade':{'base':4,'plus':2},
                 'max_upgrade_level':{'base':0,'plus':9},'unlocked':0}]},
                 'story':[{'progress':0,'stages':[{'treasure':0}]} for _ in range(10)]}
        for path in ('identity','level','plus','treasure'):
            after=copy.deepcopy(before)
            if path=='identity': after['inquiry_code']='foreign-test'
            elif path=='level': after['cats']['cats'][0]['upgrade']['base']=60
            elif path=='plus': after['cats']['cats'][0]['max_upgrade_level']['plus']=60
            else: after['story'][5]['stages'][0]['treasure']=3
            with self.assertRaisesRegex(ValueError,'PC_PROFILE_UNAPPROVED_FIELD_CHANGE'):
                verify_unchanged(before,after)
        after=copy.deepcopy(before)
        after['cats']['cats'][0]['max_upgrade_level']['base']=40
        after['story'][4]['stages'][0]['treasure']=3
        verify_unchanged(before,after)


if __name__=='__main__': unittest.main()
