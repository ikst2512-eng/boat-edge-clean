"""No-network write-once tests for research-only official source+shadow Git store."""
import base64
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from scripts.persist_official_research_bundle import (
    JST, SOURCE_FILES, blob_sha, build_bundle, store_once,
)


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.race = '202611110711'
        self.received = '2026-11-11T19:37:21+09:00'
        self.generated = '2026-11-11T19:37:40+09:00'
        self.cutoff = '2026-11-11T19:46:00+09:00'
        self.dirs = {}
        sources = {}
        for kind, filename in SOURCE_FILES.items():
            path = self.root/kind
            path.mkdir()
            raw = (kind+': real-original-payload').encode()
            (path/filename).write_bytes(raw)
            self.dirs[kind] = path
            sources[kind] = {'bytes': len(raw),
                             'sha256': hashlib.sha256(raw).hexdigest(),
                             'received_at_jst': self.received}
        manifest = {'schema':'OFFICIAL_REAUDITED_INPUT_MANIFEST_V1',
                    'race_code':self.race, 'cutoff_jst':self.cutoff,
                    'official_source_fields_reconstructed':True,
                    'formal_t12_certified':False,
                    'final_race_entry_verified':False,
                    'independent_remote_first_seen_verified':False,
                    'input_sha256':'a'*64,
                    'official_sources':sources,
                    'six_boat_inputs':[{'lane':i,'exhibition_course':i,
                                        'registration':str(3900+i)} for i in range(1,7)]}
        shadow = {'schema':'OFFICIAL_SIX_LANE_RESEARCH_SHADOW_V1',
                  'race_code':self.race, 'status':'research_shadow_generated_pre_t12',
                  'generated':True, 'generated_at_jst':self.generated,
                  't12_cutoff_jst':self.cutoff,
                  'latest_official_source_received_jst':self.received,
                  'official_input_sha256':'a'*64,
                  'model_consumed_official_exhibition_fields':True,
                  'formal_t12_certified':False,
                  'independent_remote_first_seen_verified':False,
                  'purchase_approved':False, 'research_only':True,
                  'predictions':{'balance':{'tickets':[]}}}
        inputs = {key: manifest[key] for key in
                  ('race_code','cutoff_jst','official_sources','six_boat_inputs')}
        digest = hashlib.sha256(json.dumps(
            inputs, ensure_ascii=False, sort_keys=True, separators=(',',':')
        ).encode()).hexdigest()
        manifest['input_sha256'] = digest
        shadow['official_input_sha256'] = digest
        self.row = {'race_code':self.race,
                    'formal_t12_certified':False,
                    'official_original_status':'three_originals_reaudited_research_only',
                    'official_input_manifest':manifest,
                    'official_research_shadow':shadow}

    def refresh_input_digest(self):
        manifest = self.row['official_input_manifest']
        keys = ('race_code', 'cutoff_jst', 'official_sources', 'six_boat_inputs')
        digest = hashlib.sha256(json.dumps(
            {key: manifest[key] for key in keys},
            ensure_ascii=False, sort_keys=True, separators=(',', ':')
        ).encode()).hexdigest()
        manifest['input_sha256'] = digest
        self.row['official_research_shadow']['official_input_sha256'] = digest

    def test_immutable_bundle_includes_all_actual_bytes(self):
        path, body, cutoff = build_bundle(self.row, self.dirs)
        self.assertEqual(path, 'official_source_forecast_bundles/20261111/202611110711.json')
        self.assertEqual(cutoff.isoformat(), self.cutoff)
        bundle = json.loads(body)
        self.assertFalse(bundle['formal'])
        self.assertFalse(bundle['independent_remote_first_seen_verified'])
        for kind, fname in SOURCE_FILES.items():
            got = base64.b64decode(bundle['official_raw_originals'][kind]['base64'])
            self.assertEqual(got, (self.dirs[kind]/fname).read_bytes())

    def test_manifest_digest_rechecked_after_handoff(self):
        self.row['official_input_manifest']['six_boat_inputs'][0]['exhibition_course'] = 6
        self.row['official_input_manifest']['six_boat_inputs'][5]['exhibition_course'] = 1
        with self.assertRaisesRegex(ValueError,'official_input_manifest_sha_mismatch'):
            build_bundle(self.row,self.dirs)

    def test_wrong_raw_bytes_fail_closed(self):
        (self.dirs['odds']/SOURCE_FILES['odds']).write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'original_bytes_hash_or_receipt'):
            build_bundle(self.row, self.dirs)

    def test_receipt_after_generation_fail_closed(self):
        self.row['official_input_manifest']['official_sources']['racelist']['received_at_jst'] = (
            '2026-11-11T19:37:41+09:00')
        self.refresh_input_digest()
        with self.assertRaisesRegex(ValueError,'original_bytes_hash_or_receipt'):
            build_bundle(self.row, self.dirs)

    def test_no_formal_forecast_or_missing_lane(self):
        self.row['official_research_shadow']['formal_t12_certified'] = True
        with self.assertRaisesRegex(ValueError,'not_a_research_only'):
            build_bundle(self.row, self.dirs)
        self.row['official_research_shadow']['formal_t12_certified'] = False
        self.row['official_input_manifest']['six_boat_inputs'][1]['lane'] = 1
        self.refresh_input_digest()
        with self.assertRaisesRegex(ValueError,'six_lanes'):
            build_bundle(self.row, self.dirs)

    def test_write_once_readback_and_identical_reuse(self):
        path, body, cutoff = build_bundle(self.row, self.dirs)
        files = {}
        commits = []
        def get(method, item, token, data=None):
            self.assertEqual(method,'GET')
            if item not in files:
                return 404, {}
            raw = files[item]
            return 200, {'encoding':'base64',
                         'content':base64.b64encode(raw).decode(),
                         'sha':blob_sha(raw)}
        def put(method, item, token, data=None):
            self.assertEqual(method,'PUT')
            self.assertNotIn(item, files)
            files[item] = base64.b64decode(data['content'])
            commits.append(data)
            return 201, {'content':{'sha':blob_sha(files[item])},
                         'commit':{'sha':'b'*40}}
        clock = lambda: datetime(2026,11,11,19,42,tzinfo=JST)
        a = store_once(path, body, cutoff, 'test',getter=get,putter=put,clock=clock)
        self.assertTrue(a['newly_stored'])
        self.assertFalse(a['independent_remote_first_seen_verified'])
        self.assertEqual(a['git_commit_sha'],'b'*40)
        b = store_once(path, body, cutoff, 'test',getter=get,putter=put,clock=clock)
        self.assertEqual(b['status'],'preexisting_identical_reused')
        self.assertEqual(len(commits),1)
        with self.assertRaisesRegex(RuntimeError,'immutable_path_content_conflict'):
            store_once(path,b'other',cutoff,'test',getter=get,putter=put,clock=clock)

    def test_cutoff_guard_blocks_all_network_calls(self):
        path, body, cutoff = build_bundle(self.row, self.dirs)
        def forbidden(*args,**kwargs):
            raise AssertionError('network access after cutoff approach')
        clock = lambda: datetime(2026,11,11,19,45,30,tzinfo=JST)
        a = store_once(path,body,cutoff,'test',getter=forbidden,putter=forbidden,clock=clock)
        self.assertEqual(a['status'],'cutoff_near_or_passed_no_write')

    def test_write_permission_isolated_from_pull_request_capture(self):
        workflow=(Path(__file__).resolve().parents[1] /
                  '.github/workflows/research-live-preview-evidence.yml').read_text()
        self.assertIn("permissions:\n  # Untrusted PR tests and official collection MUST remain read-only.\n  contents: read",workflow)
        self.assertIn("\n  persist-official-research:\n",workflow)
        self.assertIn("    permissions:\n      contents: write",workflow)
        self.assertIn("github.repository == 'ikst2512-eng/boat-edge-clean'",workflow)
        self.assertIn("github.ref == 'refs/heads/main'",workflow)
        self.assertIn("(github.event_name == 'schedule' || github.event_name == 'workflow_dispatch')",workflow)
        self.assertNotIn("github.event_name == 'pull_request' || github.event_name == 'workflow_dispatch'",workflow)

    def test_noncanonical_namespace_rejected(self):
        _, body, cutoff = build_bundle(self.row, self.dirs)
        with self.assertRaisesRegex(ValueError,'namespace'):
            store_once('t12_baselines/20261111/old.json',body,cutoff,'test')

if __name__ == '__main__':
    unittest.main()
