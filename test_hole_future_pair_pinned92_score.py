"""Exact-artifact, early evidence, result availability, and fail-closed tests."""
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import hole_future_pair_pinned92_score as s

JST=timezone(timedelta(hours=9))
BASE=['1-2-3','1-2-4','1-3-2','1-3-4','2-1-3','2-1-4','2-3-1','2-3-4','3-1-2','3-1-4']

def make_record(blob):
    sha=hashlib.sha256(blob).hexdigest()
    git_blob=hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()
    other=BASE[:5]+['1-4-2']+BASE[5:9]
    picks={'baseline':BASE[:], 'same_pair_two_thirds':other, 'two_pairs_one_third':BASE[:]}
    return {'schema':'HOLE_PAIR_FUTURE_FREEZE_V1','method_source_sha256':s.METHOD_SHA256,
            'status':'locally_frozen_unverified','race_code':'202611060101',
            'deadline_jst':'2026-11-06T15:20:00+09:00',
            't_minus_12_jst':'2026-11-06T15:08:00+09:00',
            'local_start_jst':'2026-11-06T12:25:24+09:00',
            'local_finish_jst':'2026-11-06T12:25:24.5+09:00',
            'source_sha256':sha,'source_git_blob_sha1':git_blob,
            'candidates':picks,'candidates_sha256':s._digest(picks),
            'formal':False,'prospective_validation':False,
            'independent_first_receipt_verified':False,'production_forecast_changed':False}

def document(record):
    return {'schema':'HOLE_PAIR_FUTURE_ACTIONS_BATCH_V1',
            'status':'local_predeadline_freeze_not_formal',
            'source_main_commit':s.SOURCE_MAIN_COMMIT,
            'capture_day_jst':'20261106',
            'frozen_count':1,'eligible_forecasts_examined':130,
            'excluded_by_reason':{'after_t_minus_12':38},
            'formal':False,'prospective_validation':False,
            'independent_first_receipt_verified':False,'production_forecast_changed':False,
            'records':[record]}

class PinnedFutureAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.blob=b'immutably captured original archive'
        path=self.root/'four_mode_forecasts';path.mkdir()
        (path/'202611060101.json').write_bytes(self.blob)
        self.record=make_record(self.blob)
        self.path=self.root/'research_candidate_freeze.json'
        self._write(document(self.record))

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, data):
        self.path.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
        self.digest=hashlib.sha256(self.path.read_bytes()).hexdigest()

    def _score(self, fn, *, digest=None):
        return s.score(self.path,self.root,fn,
                       expected_count=1,expected_digest=digest or self.digest)

    def test_pending_is_not_a_missed_prediction(self):
        r=self._score(lambda *_: {'status':'result_not_yet_confirmed','comparable':0})
        self.assertEqual(r['scored_nonformal'],0)
        self.assertEqual(r['dispositions'],{'pending_independent_result':1})
        self.assertEqual(r['hits']['baseline']['top10'],0)
        self.assertFalse(r['formal'])

    def test_one_confirmed_gain_and_protected_top5(self):
        def reviewer(*_):
            ranks={'baseline':0,'same_pair_two_thirds':6,'two_pairs_one_third':0}
            flags={k:{f'top{n}':0<rank<=n for n in s.TOPS} for k,rank in ranks.items()}
            return {'status':'reference_scored_without_independent_receipt',
                    'comparable':1,'ranks':ranks,'flags':flags}
        r=self._score(reviewer)
        self.assertEqual(r['scored_nonformal'],1)
        self.assertEqual(r['hits']['same_pair_two_thirds']['top10'],1)
        self.assertEqual(r['gained']['same_pair_two_thirds']['top10'],1)
        self.assertEqual(r['lost']['same_pair_two_thirds']['top10'],0)
        self.assertEqual(r['hits']['same_pair_two_thirds']['top5'],0)
        self.assertFalse(r['prospective_validation'])

    def test_tampered_batch_is_rejected_before_opening_result(self):
        self.path.write_bytes(self.path.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'digest_mismatch'):
            self._score(lambda *_: self.fail('opened results'))

    def test_candidate_edit_with_updated_outer_digest_still_rejected(self):
        doc=document(self.record)
        doc['records'][0]['candidates']['baseline'][0]='5-6-1'
        self._write(doc)
        with self.assertRaisesRegex(ValueError,'invalid_frozen_candidate'):
            self._score(lambda *_: self.fail('opened results'))

    def test_cutoff_must_follow_external_artifact_creation(self):
        doc=document(self.record)
        doc['records'][0]['t_minus_12_jst']='2026-11-06T12:25:25+09:00'
        doc['records'][0]['deadline_jst']='2026-11-06T12:37:25+09:00'
        self._write(doc)
        with self.assertRaisesRegex(ValueError,'invalid_frozen_candidate'):
            self._score(lambda *_: self.fail('opened results'))

    def test_changed_source_cannot_be_scored(self):
        (self.root/'four_mode_forecasts'/'202611060101.json').write_text('changed')
        r=self._score(lambda *_: self.fail('opened results'))
        self.assertEqual(r['dispositions'],{'source_fingerprint_mismatch':1})
        self.assertEqual(r['scored_nonformal'],0)

    def test_prohibited_top5_change_is_rejected(self):
        doc=document(self.record)
        doc['records'][0]['candidates']['same_pair_two_thirds'][0]='1-4-5'
        doc['records'][0]['candidates_sha256']=s._digest(doc['records'][0]['candidates'])
        self._write(doc)
        with self.assertRaisesRegex(ValueError,'invalid_frozen_candidate'):
            self._score(lambda *_: self.fail('opened results'))

    def test_invalid_review_flags_fail_closed(self):
        def reviewer(*_):
            ranks={'baseline':0,'same_pair_two_thirds':6,'two_pairs_one_third':0}
            flags={k:{f'top{n}':False for n in s.TOPS} for k in s.POLICIES}
            return {'status':'reference_scored_without_independent_receipt',
                    'comparable':1,'ranks':ranks,'flags':flags}
        with self.assertRaisesRegex(ValueError,'invalid_review_flag'):
            self._score(reviewer)

    def test_officially_cancelled_race_is_neither_pending_nor_miss(self):
        self.record['race_code'] = '202611060806'
        (self.root/'four_mode_forecasts'/'202611060806.json').write_bytes(self.blob)
        self._write(document(self.record))
        r = self._score(lambda *_: self.fail('cancelled race opened result reviewer'))
        self.assertEqual(r['scored_nonformal'], 0)
        self.assertEqual(r['dispositions'], {'officially_cancelled_no_result': 1})
        self.assertEqual(r['officially_cancelled_codes'], ['202611060806'])
        self.assertFalse(r['formal'])

    def test_officially_cancelled_race_with_result_file_is_rejected(self):
        self.record['race_code'] = '202611060806'
        (self.root/'four_mode_forecasts'/'202611060806.json').write_bytes(self.blob)
        result_dir = self.root/'confirmed_results'
        result_dir.mkdir()
        (result_dir/'202611060806.json').write_text('{"status":"confirmed"}')
        self._write(document(self.record))
        with self.assertRaisesRegex(ValueError, 'cancelled_race_has_result_file'):
            self._score(lambda *_: self.fail('cancelled race opened result reviewer'))

    def test_present_invalid_result_cannot_be_silently_pending(self):
        results = self.root/'confirmed_results'
        results.mkdir()
        (results/'202611060101.json').write_text('{"status":"untrusted"}')
        with self.assertRaisesRegex(ValueError, 'saved_result_exists_but_untrusted'):
            self._score(lambda *_: {'status':'result_not_yet_confirmed','comparable':0})

    def test_pr_ci_does_not_repeat_candidate_freeze(self):
        # Code changes must not create another overlapping shadow artifact.
        workflow = (Path(__file__).resolve().parent/
                    '.github/workflows/hole-future-pair-precommit.yml').read_text()
        self.assertIn(
            "- name: Freeze future race candidates from immutable main forecasts (research only)\n"
            "        if: github.event_name == 'workflow_dispatch'",
            workflow)
        self.assertIn(
            "- uses: actions/upload-artifact@v4\n"
            "        if: github.event_name == 'workflow_dispatch'\n"
            "        with:\n"
            "          name: hole-future-pair-precutoff-candidates",
            workflow)

if __name__=='__main__': unittest.main()
