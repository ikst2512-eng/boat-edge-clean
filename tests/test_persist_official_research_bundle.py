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
    verify_independent_source_and_shadow_replay, receipt_snapshot,
    bind_same_action_source_paths, verify_commit_initial_add,
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
        commit_fetcher = lambda sha, token: {
            'sha': sha, 'files': [{'filename': path, 'status': 'added', 'sha': blob_sha(body)}]
        }
        a = store_once(path, body, cutoff, 'test',getter=get,putter=put,
                       commit_fetcher=commit_fetcher,clock=clock)
        self.assertTrue(a['newly_stored'])
        self.assertFalse(a['independent_remote_first_seen_verified'])
        self.assertEqual(a['git_commit_sha'],'b'*40)
        self.assertEqual(a['git_blob_sha1'], blob_sha(body))
        self.assertEqual(a['put_response_observed_at_jst'], '2026-11-11T19:42:00+09:00')
        self.assertEqual(a['readback_response_observed_at_jst'], '2026-11-11T19:42:00+09:00')
        self.assertEqual(a['sha256'], hashlib.sha256(body).hexdigest())
        self.assertTrue(a['git_commit_added_path_verified'])
        self.assertEqual(a['git_commit_file_status'], 'added')
        self.assertEqual(a['git_commit_file_blob_sha1'], blob_sha(body))
        self.assertEqual(a['commit_status_observed_at_jst'], '2026-11-11T19:42:00+09:00')
        b = store_once(path, body, cutoff, 'test',getter=get,putter=put,clock=clock)
        self.assertEqual(b['status'],'preexisting_identical_reused')
        self.assertEqual(len(commits),1)
        with self.assertRaisesRegex(RuntimeError,'immutable_path_content_conflict'):
            store_once(path,b'other',cutoff,'test',getter=get,putter=put,clock=clock)

    def test_git_commit_status_is_added_not_modified(self):
        path,body,cutoff=build_bundle(self.row,self.dirs)
        def details(status='added',filename=None,sha=None,files=None):
            return {'sha':'a'*40,'files': files if files is not None else [{
                'filename': filename or path,'status':status,'sha':sha or blob_sha(body)}]}
        result=verify_commit_initial_add(
            'a'*40,path,body,'token',commit_fetcher=lambda a,b:details())
        self.assertTrue(result['git_commit_added_path_verified'])
        for item in (details(status='modified'),
                     details(filename='t12_baselines/20261111/old.json'),
                     details(sha='b'*40),
                     details(files=[]),
                     {'sha':'c'*40,'files':details()['files']},
                     details(files=details()['files']*2)):
            with self.assertRaisesRegex(RuntimeError, 'git_initial_add_'):
                verify_commit_initial_add(
                    'a'*40,path,body,'token',commit_fetcher=lambda a,b,item=item:item)

    def test_git_commit_read_error_never_claims_initial_add(self):
        path,body,cutoff=build_bundle(self.row,self.dirs)
        def failed_commit(*args):
            raise RuntimeError('git_initial_add_commit_identity_unverified')
        with self.assertRaisesRegex(RuntimeError,'git_initial_add_'):
            verify_commit_initial_add('a'*40,path,body,'token',
                                      commit_fetcher=failed_commit)

    def test_cutoff_guard_blocks_all_network_calls(self):
        path, body, cutoff = build_bundle(self.row, self.dirs)
        def forbidden(*args,**kwargs):
            raise AssertionError('network access after cutoff approach')
        clock = lambda: datetime(2026,11,11,19,45,30,tzinfo=JST)
        a = store_once(path,body,cutoff,'test',getter=forbidden,putter=forbidden,clock=clock)
        self.assertEqual(a['status'],'cutoff_near_or_passed_no_write')

    def test_privileged_job_replays_source_and_prediction(self):
        original_manifest=json.loads(json.dumps(self.row['official_input_manifest']))
        original_shadow=json.loads(json.dumps(self.row['official_research_shadow']))
        calls=[]
        official={
            'race_code':self.race,
            'all_research_components_observed_by_t12':True,
            'three_originals_hash_verified':True,
            'missing_components':[],
            'final_race_entry_verified':False
        }
        def auditor(*folders):
            calls.append([Path(x).name for x in folders])
            return official
        rebuild_manifest=lambda folders, audit: original_manifest
        rebuild_shadow=lambda manifest, stamp: original_shadow

        self.assertTrue(verify_independent_source_and_shadow_replay(
            self.row,self.dirs,auditor=auditor,
            manifest_builder=rebuild_manifest,shadow_builder=rebuild_shadow))
        self.assertEqual(calls,[list(SOURCE_FILES)])

        self.row['official_research_shadow']['predictions']['balance']['tickets'].append('2-3-1')
        with self.assertRaisesRegex(ValueError,'privileged_shadow_predictions_replay_mismatch'):
            verify_independent_source_and_shadow_replay(
                self.row,self.dirs,auditor=auditor,
                manifest_builder=rebuild_manifest,shadow_builder=rebuild_shadow)

        self.row['official_research_shadow']=original_shadow
        self.row['official_input_manifest']['official_sources']['odds']['sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'privileged_original_manifest_replay_mismatch'):
            verify_independent_source_and_shadow_replay(
                self.row,self.dirs,auditor=auditor,
                manifest_builder=rebuild_manifest,shadow_builder=rebuild_shadow)

    def test_privileged_job_rejects_incomplete_official_triple(self):
        incomplete={'race_code':self.race,
                    'all_research_components_observed_by_t12':False,
                    'three_originals_hash_verified':True,
                    'missing_components':['odds_120'],
                    'final_race_entry_verified':False}
        def forbidden(*args):
            raise AssertionError('missing triple must not reach manifest/forecast')
        with self.assertRaisesRegex(ValueError,'privileged_official_three_source_reaudit_failed'):
            verify_independent_source_and_shadow_replay(
                self.row,self.dirs,auditor=lambda *paths: incomplete,
                manifest_builder=forbidden,shadow_builder=forbidden)

    def test_concurrent_git_409_is_not_hidden_or_retried(self):
        path, body, cutoff = build_bundle(self.row, self.dirs)
        attempts=[]
        def missing(method,item,token,data=None):
            return 404, {}
        def conflict(method,item,token,data=None):
            attempts.append((method,item))
            return 409, {}
        clock=lambda:datetime(2026,11,11,19,42,tzinfo=JST)
        with self.assertRaisesRegex(RuntimeError,'git_create_unverified_or_too_late_http_409'):
            store_once(path,body,cutoff,'test',getter=missing,
                       putter=conflict,clock=clock)
        self.assertEqual(attempts,[('PUT',path)])

    def test_github_response_after_cutoff_is_never_certified(self):
        path, body, cutoff = build_bundle(self.row, self.dirs)
        stamps=iter([datetime(2026,11,11,19,42,tzinfo=JST),
                     datetime(2026,11,11,19,42,tzinfo=JST),
                     datetime(2026,11,11,19,46,tzinfo=JST)])
        def missing(method,item,token,data=None):
            return 404, {}
        def accepted(method,item,token,data=None):
            return 201,{'content':{'sha':blob_sha(body)},
                        'commit':{'sha':'b'*40}}
        with self.assertRaisesRegex(RuntimeError,'git_create_unverified_or_too_late_http_201'):
            store_once(path,body,cutoff,'test',getter=missing,
                       putter=accepted,clock=lambda:next(stamps))

    def test_source_folders_bound_to_current_action_run(self):
        run = '43007171927'
        roots = {
            'racelist': self.root / ('racelist_run'+run)/'20261111'/self.race,
            'beforeinfo': self.root / ('before_run'+run)/'20261111'/self.race,
            'odds': self.root / ('odds_run'+run)/'20261111'/self.race,
        }
        context = bind_same_action_source_paths(
            roots, run_id=run, run_attempt='1', event='workflow_dispatch',
            head_sha='b'*40)
        self.assertEqual(context['source_collection_action_run_id'],run)
        self.assertTrue(context['same_run_source_paths_verified'])
        self.assertFalse(context['independent_remote_first_seen_verified'])
        path, body, _ = build_bundle(
            self.row,self.dirs,capture_action_context=context)
        content=json.loads(body)
        self.assertEqual(content['capture_action_context'],context)
        self.assertFalse(content['formal'])
        roots['odds']=self.root / 'odds_run43005555555'/'20261111'/self.race
        with self.assertRaisesRegex(ValueError,'source_folder_not_from_current_action'):
            bind_same_action_source_paths(
                roots,run_id=run,run_attempt='1',event='workflow_dispatch',head_sha='b'*40)

    def test_reject_forged_capture_context_and_missing_action_metadata(self):
        with self.assertRaisesRegex(ValueError,'capture_action_context_not_proven'):
            build_bundle(self.row,self.dirs,capture_action_context={
                'source_collection_action_run_id':'43007171927'})
        roots = {kind:self.root / (kind+'_run43007171927')/'20261111'/self.race
                 for kind in SOURCE_FILES}
        with self.assertRaisesRegex(ValueError,'capture_action_context_invalid'):
            bind_same_action_source_paths(
                roots,run_id='43007171927',run_attempt='1',event='pull_request',
                head_sha='b'*40)
        with self.assertRaisesRegex(ValueError,'capture_action_context_invalid'):
            bind_same_action_source_paths(
                roots,run_id='43007171927',run_attempt='1',event='schedule',
                head_sha='not-40hex')
        with self.assertRaisesRegex(ValueError,'capture_action_context_invalid'):
            bind_same_action_source_paths(
                roots,run_id='not-an-id',run_attempt='1',event='schedule',
                head_sha='b'*40)

    def test_action_receipt_identifies_write_and_remains_nonformal(self):
        outcomes = [
            {'race_code': self.race, 'path': 'official_source_forecast_bundles/20261111/'+self.race+'.json',
             'status': 'new_research_bundle_first_add_put_and_get_matched',
             'git_commit_sha': 'b'*40, 'sha256': 'c'*64, 'newly_stored': True},
            {'race_code': '202611112411', 'status': 'cutoff_near_or_passed_no_write',
             'stored': False},
        ]
        audit = receipt_snapshot(
            outcomes, status='checked', event='workflow_dispatch',
            run_id='43017934660', run_attempt='1',
            observed_at_jst='2026-11-11T21:09:59+09:00')
        self.assertEqual(audit['newly_stored'], 1)
        self.assertEqual(audit['action_event'], 'workflow_dispatch')
        self.assertFalse(audit['independent_remote_first_seen_verified'])
        self.assertFalse(audit['formal_t12_certified'])
        self.assertFalse(audit['purchase_approved'])
        self.assertNotIn('GH_TOKEN', json.dumps(audit))
        self.assertNotIn('official_raw_originals', json.dumps(audit))

    def test_action_receipt_never_masks_failed_or_ambiguous_writer(self):
        audit = receipt_snapshot(
            [], status='failed', event='schedule', run_id='9',
            run_attempt='1', observed_at_jst='2026-11-11T21:09:59+09:00',
            error_type='RuntimeError',
            error_code='git_create_unverified_or_too_late_http_409')
        self.assertEqual(audit['newly_stored'], 0)
        self.assertEqual(audit['status'], 'failed')
        self.assertEqual(audit['error_code'], 'git_create_unverified_or_too_late_http_409')
        self.assertIs(audit['independent_remote_first_seen_verified'], False)
        with self.assertRaisesRegex(ValueError, 'invalid_git_store_audit_status'):
            receipt_snapshot([], status='success', event='schedule',
                             run_id='9', run_attempt='1',
                             observed_at_jst='2026-11-11T21:09:59+09:00')

    def test_privileged_main_handoff_receipt_and_event_guard_without_network(self):
        """Exercise main() with the actual artifact directory layout and no Git HTTP."""
        import os
        import shutil
        import sys
        from unittest.mock import patch
        from scripts import persist_official_research_bundle as writer

        run_id = '43007171927'
        batch = self.root / 'official_joint_evidence'
        observations = batch / 'observations'
        for kind, filename in SOURCE_FILES.items():
            prefix = {'racelist': 'racelist_', 'beforeinfo': 'before_', 'odds': 'odds_'}[kind]
            target = observations / (prefix + 'run' + run_id) / '20261111' / self.race
            target.mkdir(parents=True)
            shutil.copyfile(self.dirs[kind] / filename, target / filename)
            (target / 'manifest.json').write_text('{}', encoding='utf-8')
        report = {
            'status': 'read_only_research_audited',
            'formal_t12_certified': 0,
            'official_consumed_forecasts': 0,
            'rows': [self.row],
        }
        (batch / 'forecast_temporal_link_report.json').write_text(
            json.dumps(report), encoding='utf-8')
        receipt_path = self.root / 'official-source-git-receipt' / 'receipt.json'
        cli = ['persist_official_research_bundle.py', '--batch-dir', str(batch),
               '--receipt-output', str(receipt_path)]
        env = {
            'GITHUB_REPOSITORY': 'ikst2512-eng/boat-edge-clean',
            'GITHUB_REF': 'refs/heads/main',
            'GITHUB_EVENT_NAME': 'workflow_dispatch',
            'GITHUB_RUN_ID': run_id,
            'GITHUB_RUN_ATTEMPT': '1',
            'GITHUB_SHA': 'b' * 40,
            'GH_TOKEN': 'unreachable-test-token',
        }
        expected = {
            'status': 'new_research_bundle_first_add_put_and_get_matched',
            'stored': True, 'newly_stored': True,
            'git_commit_sha': 'c' * 40,
            'git_commit_added_path_verified': True,
        }
        with patch.dict(os.environ, env), patch.object(sys, 'argv', cli), (
                patch.object(writer, 'verify_independent_source_and_shadow_replay',
                             return_value=True) as replay), (
                patch.object(writer, 'store_once', return_value=expected) as store):
            writer.main()
        result = json.loads(receipt_path.read_text(encoding='utf-8'))
        self.assertEqual(result['status'], 'checked')
        self.assertEqual(result['newly_stored'], 1)
        self.assertEqual(result['action_run_id'], run_id)
        self.assertFalse(result['formal_t12_certified'])
        self.assertFalse(result['independent_remote_first_seen_verified'])
        self.assertEqual(result['outcomes'][0]['race_code'], self.race)
        self.assertEqual(result['outcomes'][0]['git_commit_sha'], 'c' * 40)
        replay.assert_called_once()
        store.assert_called_once()
        persisted = json.loads(store.call_args.args[1])
        self.assertEqual(persisted['capture_action_context'][
            'source_collection_action_run_id'], run_id)
        self.assertEqual(set(persisted['official_raw_originals']), set(SOURCE_FILES))
        self.assertFalse(persisted['formal'])

        # Non-main, including PR code, must fail before ANY write or replay.
        rejected = self.root / 'official-source-git-receipt' / 'rejected.json'
        bad_cli = cli[:]
        bad_cli[-1] = str(rejected)
        with patch.dict(os.environ, {**env, 'GITHUB_REF': 'refs/heads/feature'}), (
                patch.object(sys, 'argv', bad_cli)), (
                patch.object(writer, 'verify_independent_source_and_shadow_replay',
                             side_effect=AssertionError('replay forbidden'))), (
                patch.object(writer, 'store_once',
                             side_effect=AssertionError('write forbidden'))):
            with self.assertRaisesRegex(ValueError, 'guarded_non_main'):
                writer.main()
        denied = json.loads(rejected.read_text(encoding='utf-8'))
        self.assertEqual(denied['status'], 'failed')
        self.assertEqual(denied['newly_stored'], 0)
        self.assertEqual(denied['error_code'], 'guarded_non_main_or_non_scheduled_event')

    def test_writer_receipt_artifact_is_retained_on_failure(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    '.github/workflows/research-live-preview-evidence.yml').read_text()
        self.assertIn('name: official-research-git-receipt-${{ github.run_id }}-${{ github.run_attempt }}', workflow)
        self.assertIn('path: official-source-git-receipt/receipt.json', workflow)
        self.assertIn('if-no-files-found: warn', workflow)
        self.assertIn('      - name: Retain immutable Git write/readback receipt as independent Action artifact\n        if: always()', workflow)

    def test_write_permission_isolated_from_pull_request_capture(self):
        workflow=(Path(__file__).resolve().parents[1] /
                  '.github/workflows/research-live-preview-evidence.yml').read_text()
        self.assertIn("permissions:\n  # Untrusted PR tests and official collection MUST remain read-only.\n  contents: read",workflow)
        self.assertIn("\n  persist-official-research:\n",workflow)
        self.assertIn("    permissions:\n      contents: write",workflow)
        self.assertIn("needs.capture.result == 'success'",workflow)
        self.assertIn("needs.capture.outputs.official_bundle_ready == 'true'",workflow)
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
