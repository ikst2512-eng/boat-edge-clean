import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from scripts import archive_legacy_p0_originals as mod


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], stderr=subprocess.DEVNULL).decode().strip()


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root/'legacy'
        self.repo.mkdir()
        subprocess.run(['git', '-C', str(self.repo), 'init', '-q'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'config', 'user.name', 'Tests'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'config', 'user.email', 'tests@example.test'], check=True)
        self.path = 'data/site_prediction_snapshots/20261008-01-04.json'
        full = self.repo/self.path
        full.parent.mkdir(parents=True)
        self.raw = b'{"source":"immutable"}\n'
        full.write_bytes(self.raw)
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'commit', '-q', '-m', 'fixture'], check=True)
        self.commit = git(self.repo, 'rev-parse', 'HEAD')
        self.original_pin = mod.LEGACY_PIN
        self.clean_pin = mod.CLEAN_PIN
        mod.LEGACY_PIN = self.commit
        mod.CLEAN_PIN = '1' * 40
        self.addCleanup(self.reset)
        self.legacy_tree = {'sha': self.commit, 'truncated': False, 'tree': [
            {'type': 'blob', 'path': self.path, 'sha': mod.blob_hash(self.raw)}]}
        self.clean_tree = {'sha': '1' * 40, 'truncated': False, 'tree': []}

    def reset(self):
        mod.LEGACY_PIN = self.original_pin
        mod.CLEAN_PIN = self.clean_pin

    def test_small_archive_roundtrip_preserves_exact_bytes(self):
        out = self.root/'new.zip'
        data = mod.archive(self.repo, out, self.legacy_tree, self.clean_tree,
                           strict=False, execute=True)
        self.assertEqual(data['sources_rechecked'], 1)
        self.assertFalse(data['independent_offsite_restored'])
        self.assertFalse(data['delete_authorized'])
        with zipfile.ZipFile(out) as z:
            self.assertEqual(z.read('originals/'+self.commit+'/'+self.path), self.raw)
            manifest = json.loads(z.read('originals_manifest.json'))
            self.assertEqual(manifest['files'][0]['git_blob_sha1'], mod.blob_hash(self.raw))
            self.assertFalse(manifest['independent_offsite_restored'])
        with self.assertRaises(FileExistsError):
            mod.archive(self.repo, out, self.legacy_tree, self.clean_tree,
                        strict=False, execute=True)

    def test_different_source_content_rejected(self):
        self.legacy_tree['tree'][0]['sha'] = 'a'*40
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            mod.archive(self.repo, self.root/'out.zip', self.legacy_tree,
                        self.clean_tree, strict=False, execute=True)

    def test_race_present_in_clean_excluded(self):
        self.clean_tree['tree'] = [{'type':'blob',
               'path':'confirmed_results/202610080104.json', 'sha':'a'*40}]
        rows, p0, missing = mod.inventory(self.legacy_tree, self.clean_tree, strict=False)
        self.assertEqual(rows, [])
        self.assertEqual(len(p0), 0)

    def test_missing_snapshot_not_p0(self):
        self.legacy_tree['tree'][0]['path'] = 'data/site_odds/20261008-01-04.json'
        rows, p0, _ = mod.inventory(self.legacy_tree, self.clean_tree, strict=False)
        self.assertEqual(rows, [])
        self.assertEqual(len(p0), 0)

    def test_fail_closed_malformed_source_tree(self):
        self.legacy_tree['truncated'] = True
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            mod.inventory(self.legacy_tree, self.clean_tree, strict=False)

    def test_bad_path_source_sha_is_rejected(self):
        self.legacy_tree['tree'][0]['sha'] = 'bad'
        with self.assertRaisesRegex(ValueError, 'SHA'):
            mod.inventory(self.legacy_tree, self.clean_tree, strict=False)

    def test_strict_inventory_does_not_claim_one_race_is_full(self):
        with self.assertRaisesRegex(ValueError, 'drift'):
            mod.inventory(self.legacy_tree, self.clean_tree, strict=True)

if __name__ == '__main__':
    unittest.main()
