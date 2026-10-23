import unittest
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace as N
from tools.pc_profile_install import journal_action, _install_locked
from tools.pc_lab import Lab, PACKAGE


class ProfileJournalTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','Windows guest-operation lock')
    def test_profile_and_capture_cannot_hold_the_guest_operation_lock_together(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            one=Lab(root/'private/pc-lab',root/'sdk',root/'java')
            two=Lab(root/'private/pc-lab',root/'sdk',root/'java')
            with one.app_operation_lock():
                with self.assertRaisesRegex(RuntimeError,'APP_OPERATION_BUSY_NO_MUTATION'):
                    with two.app_operation_lock(): self.fail('second operation acquired lock')
            with two.app_operation_lock(): pass

    def test_recovery_requires_verified_backup_and_stops_a_late_launch_before_rename(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            tx=root/'tx'; tx.mkdir()
            candidate=b'candidate'
            source=b'original'
            output_sha=hashlib.sha256(candidate).hexdigest()
            source_sha=hashlib.sha256(source).hexdigest()
            (tx/'initial-SAVE_DATA').write_bytes(candidate)
            journal=dict(schema='kneekura-pc-profile-transaction-v1',status='PREPARED',
                         boot_identity_sha256='identity',source_sha256=source_sha,
                         output_sha256=output_sha,transaction_directory='tx')
            (root/'initial-v1.json').write_text(json.dumps(journal))
            calls=[]
            live=[source_sha]
            running=[False]
            def adb(*args,**kwargs):
                calls.append(args)
                text=''; code=0
                if args[:2]==('shell','sha256sum'):
                    text=('identity' if args[2].endswith('.record') else output_sha
                          if args[2].endswith('.pending') else live[0])+'  private\n'
                elif args[:3]==('shell','am','force-stop'): running[0]=False
                elif args[:2]==('shell','pidof'): text='123\n' if running[0] else ''
                elif args[:2]==('shell','-T'): running[0]=True  # simulate external late launch
                elif args[:2]==('shell','mv'):
                    self.assertFalse(running[0]); live[0]=output_sha
                elif args[:2]==('shell','cmd'): text='package:'+PACKAGE+' uid:10209\n'
                elif len(args)==2 and args[1].startswith('test -L'): code=1
                return subprocess.CompletedProcess(args,code,text,'')
            lab=N(state=root,adb=adb)
            with self.assertRaisesRegex(ValueError,'PREPARED_BACKUP_MISSING_OR_CHANGED'):
                _install_locked(lab,root,{})
            self.assertFalse(any(c[:2]==('shell','mv') for c in calls))
            (tx/'original-SAVE_DATA').write_bytes(source)
            result=_install_locked(lab,root,{})
            self.assertTrue(result['private_backup_verified'])
            upload=next(i for i,c in enumerate(calls) if c[:2]==('shell','-T'))
            rename=next(i for i,c in enumerate(calls) if c[:2]==('shell','mv'))
            self.assertTrue(any(c[:3]==('shell','am','force-stop') for c in calls[upload:rename]))

    def test_completed_profile_never_refills_after_spending(self):
        journal=dict(schema='kneekura-pc-profile-transaction-v1',status='APPLIED',
                     boot_identity_sha256='identity',source_sha256='before',output_sha256='max')
        self.assertEqual(journal_action(journal,'identity','spent-and-played'),'NO_REFILL')

    def test_interrupted_commit_recovers_without_reapplying_changed_progress(self):
        journal=dict(schema='kneekura-pc-profile-transaction-v1',status='PREPARED',
                     boot_identity_sha256='identity',source_sha256='before',output_sha256='max')
        self.assertEqual(journal_action(journal,'identity','max'),'COMMIT_ONLY')
        self.assertEqual(journal_action(journal,'identity','before'),'APPLY')
        with self.assertRaisesRegex(ValueError,'PROFILE_TRANSACTION_CHANGED'):
            journal_action(journal,'identity','spent-and-played')
        with self.assertRaisesRegex(ValueError,'PROFILE_IDENTITY_CHANGED'):
            journal_action(journal,'foreign','before')


if __name__=='__main__': unittest.main()
