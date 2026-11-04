#!/usr/bin/env python3
"""Read-only, pinned P0 legacy original-byte archive. Never authorizes deletion.

This creates a GitHub Actions artifact only; independent offsite custody and
restore must still be verified before legacy retirement.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

LEGACY = 'ikst2512-eng/boat-edge'
CLEAN = 'ikst2512-eng/boat-edge-clean'
LEGACY_PIN = 'f38204105a979aa6ef5293d1b9cad854056faadd'
CLEAN_PIN = 'eff4975851744a9851ce82383c79662b76496747'
CATEGORIES = ('site_prediction_snapshots', 'site_prediction_audit',
              'site_prediction_history', 'site_odds', 'site_results')
LEGACY_PATTERN = re.compile(r'^data/(site_prediction_snapshots|site_prediction_audit|site_prediction_history|site_odds|site_results)/(\d{8})-(\d{2})-(\d{2})\.json$')
CLEAN_PATTERN = re.compile(r'^(confirmed_results|four_mode_forecasts|prospective_predictions|four_mode_performance)/(\d{12})\.json$')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def blob_hash(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def fetch_tree(repository, sha):
    url = f'https://api.github.com/repos/{repository}/git/trees/{sha}?recursive=1'
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'boat-edge-p0-preserver/1'}
    token = os.environ.get('GH_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    with urlopen(Request(url, headers=headers), timeout=75) as response:
        return json.load(response)


def inventory(legacy_tree, clean_tree, *, strict=True):
    """P0 is exactly legacy-only race IDs with a legacy prediction snapshot."""
    if (not isinstance(legacy_tree, dict) or not isinstance(clean_tree, dict)
            or legacy_tree.get('sha') != LEGACY_PIN or clean_tree.get('sha') != CLEAN_PIN
            or legacy_tree.get('truncated') is not False or clean_tree.get('truncated') is not False
            or not isinstance(legacy_tree.get('tree'), list)
            or not isinstance(clean_tree.get('tree'), list)):
        raise ValueError('pinned source trees unavailable or truncated')
    live_clean = set()
    for item in clean_tree['tree']:
        if not isinstance(item, dict) or item.get('type') != 'blob':
            continue
        match = CLEAN_PATTERN.fullmatch(item.get('path', ''))
        if match:
            live_clean.add(match.group(2))
    legacy = {}
    for item in legacy_tree['tree']:
        if not isinstance(item, dict) or item.get('type') != 'blob':
            continue
        path = item.get('path', '')
        match = LEGACY_PATTERN.fullmatch(path)
        if not match:
            continue
        cat, day, venue, race = match.groups()
        if not (1 <= int(venue) <= 24 and 1 <= int(race) <= 12):
            raise ValueError('invalid race identity')
        code = day + venue + race
        sha = item.get('sha')
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise ValueError('invalid Git blob SHA')
        group = legacy.setdefault(code, {})
        if cat in group:
            raise ValueError('duplicate source category')
        group[cat] = (path, sha)
    p0 = {key: value for key, value in legacy.items()
          if key not in live_clean and 'site_prediction_snapshots' in value}
    originals = sorted((code, *data) for code, group in p0.items() for data in group.values())
    missing = Counter(cat for group in p0.values() for cat in CATEGORIES if cat not in group)
    if strict and (len(legacy) != 4143 or len(p0) != 1125 or len(originals) != 5578
                   or missing != {'site_odds': 46, 'site_prediction_history': 1}):
        raise ValueError(f'pinned P0 inventory drift: legacy={len(legacy)} races={len(p0)} '
                         f'files={len(originals)} missing={dict(missing)}')
    if len({path for _, path, _ in originals}) != len(originals):
        raise ValueError('duplicate original paths')
    return originals, p0, missing


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def archive(repo, target, legacy_tree, clean_tree, *, strict=True, execute=False):
    originals, p0, missing = inventory(legacy_tree, clean_tree, strict=strict)
    repo = Path(repo).resolve(strict=True)
    if git(repo, 'rev-parse', '--verify', LEGACY_PIN + '^{commit}').decode().strip() != LEGACY_PIN:
        raise ValueError('pinned Git commit unavailable')
    target = Path(target).absolute()
    result = {'schema': 'CLEAN_P0_ORIGINAL_BYTE_ARCHIVE_V1',
              'legacy_commit': LEGACY_PIN, 'clean_commit': CLEAN_PIN,
              'p0_races': len(p0), 'originals_indexed': len(originals),
              'missing_by_source': dict(missing), 'formal': False,
              'independent_offsite_restored': False,
              'delete_authorized': False, 'legacy_writer_stop_authorized': False,
              'status': 'DRY_RUN'}
    if not execute:
        return result
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise FileExistsError('archive output already exists')
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.zip', prefix='.p0-working-', delete=False) as f:
        temp = Path(f.name)
    try:
        files = []
        with zipfile.ZipFile(temp, 'w', compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as dest:
            for race, path, expected_blob in originals:
                data = git(repo, 'show', LEGACY_PIN + ':' + path)
                if blob_hash(data) != expected_blob:
                    raise ValueError('pinned Git original byte mismatch: ' + path)
                saved_path = 'originals/' + LEGACY_PIN + '/' + path
                dest.writestr(saved_path, data)
                files.append({'race_code': race, 'path': path,
                              'git_blob_sha1': expected_blob, 'sha256': digest(data),
                              'bytes': len(data)})
            dest.writestr('originals_manifest.json', json.dumps({
                **result, 'files': files, 'status': 'ARCHIVED_NOT_INDEPENDENT_OFFSITE'},
                sort_keys=True, separators=(',', ':'), ensure_ascii=False))
        with zipfile.ZipFile(temp) as src:
            if src.testzip() is not None:
                raise ValueError('bad ZIP CRC')
            for item in files:
                content = src.read('originals/' + LEGACY_PIN + '/' + item['path'])
                if digest(content) != item['sha256'] or blob_hash(content) != item['git_blob_sha1']:
                    raise ValueError('ZIP readback corrupted: ' + item['path'])
        # No-clobber atomic publish; archive stays isolated from the checked-out repo.
        os.link(temp, target, follow_symlinks=False)
        result.update(status='LOCAL_ZIP_READBACK_VERIFIED_NOT_OFFSITE',
                      archive_sha256=digest(target.read_bytes()),
                      archive_bytes=target.stat().st_size, sources_rechecked=len(files))
        return result
    finally:
        temp.unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--legacy-repo', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--receipt', required=True)
    args = p.parse_args()
    target = Path(args.out)
    receipt = Path(args.receipt)
    if receipt.exists() or receipt.is_symlink():
        raise FileExistsError('receipt already exists')
    result = archive(args.legacy_repo, target,
                     fetch_tree(LEGACY, LEGACY_PIN), fetch_tree(CLEAN, CLEAN_PIN),
                     execute=args.execute)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open('x', encoding='utf-8') as dest:
        json.dump(result, dest, indent=2, ensure_ascii=False)
    print('LEGACY_P0_ARCHIVE ' + json.dumps(result, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
