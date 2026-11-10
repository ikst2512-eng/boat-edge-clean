import base64
import hashlib
import json
import unittest

from entry_course_archive_integrity_audit import audit_archive_bytes
from test_entry_waku10_durable_ledger import sample, raw
from test_entry_waku10_pilot import fixture

DAY="20261103"
REPO="ikst2512-eng/boat-edge-clean"
CODE="202611030708"


def t12_content():
    baseline,card,ev=fixture()
    baseline.update({
        "model_version":"national-beta0.4-exploratory-v1",
        # T-12 selection permits generation from 18:07 to before 18:21.
        # Keep this positive fixture genuinely window-timed, not cached at 18:00.
        "generated_at":"2026-11-03T18:15:00+09:00",
        "source_title_received_jst":"2026-11-03T18:15:00+09:00",
        "source_cards_received_jst":"2026-11-03T18:15:00+09:00",
        "source_title_sha256":"a"*64,
        "source_cards_sha256":"b"*64,
        "input_sha256":"c"*64,
        "model_source_sha256":"d"*64,
    })
    return (json.dumps(baseline,ensure_ascii=False,sort_keys=True)+"\n").encode()


def blob(raw_data, path):
    sha=hashlib.sha1(b"blob "+str(len(raw_data)).encode()+b"\x00"+raw_data).hexdigest()
    return ({"type":"blob","path":path,"sha":sha},
            {"sha":sha,"encoding":"base64","content":base64.b64encode(raw_data).decode()})


def records(*, changed_reference=False, corrupt_sha=False, include_t12=True):
    t12bytes=t12_content()
    waku=sample()
    if changed_reference:
        waku["reference_t12_top10"]=["1-2-3"]
    waku_raw=raw(waku)
    pairs=[blob(waku_raw,f"waku10/{DAY}/{CODE}.json")]
    if include_t12:
        pairs.append(blob(t12bytes,f"t12_baselines/{DAY}/{CODE}.json"))
    tree=[x[0] for x in pairs]
    store={x[0]["sha"]:x[1] for x in pairs}
    if corrupt_sha:
        tree[0]["sha"]="f"*40
    return tree,store


def fake_fetch(store):
    def fetch(route):
        sha=route.rsplit("/",1)[-1]
        return store[sha]
    return fetch


class ArchiveIntegrityTests(unittest.TestCase):
    def test_valid_github_blobs_twelve_and_waku_crosslinked(self):
        tree,store=records()
        out=audit_archive_bytes(DAY,tree,fake_fetch(store),repository=REPO)
        self.assertEqual(out["blob_sha_and_internal_payload_valid_count"],2)
        self.assertEqual(out["t12_payload_valid_count"],1)
        self.assertEqual(out["t2_payload_valid_count"],1)
        self.assertEqual(out["t2_reference_matched_count"],1)
        self.assertEqual(out["invalid_blob_or_payload_count"],0)
        self.assertFalse(out["independent_remote_first_add_time_verified"])
        self.assertFalse(out["pre_cutoff_git_publication_verified"])
    def test_old_cached_generation_is_not_valid_t12_even_with_matching_git_sha(self):
        stale=json.loads(t12_content())
        stale["generated_at"]="2026-11-03T18:00:00+09:00"
        stale["source_title_received_jst"]=stale["generated_at"]
        stale["source_cards_received_jst"]=stale["generated_at"]
        raw_stale=(json.dumps(stale,ensure_ascii=False,sort_keys=True)+"\\n").encode()
        pair=blob(raw_stale,f"t12_baselines/{DAY}/{CODE}.json")
        result=audit_archive_bytes(DAY,[pair[0]],
            fake_fetch({pair[0]["sha"]:pair[1]}),repository=REPO)
        self.assertEqual(result["t12_payload_valid_count"],0)
        self.assertEqual(result["invalid_blob_or_payload_count"],1)
        self.assertFalse(result["independent_remote_first_add_time_verified"])

    def test_modified_reference_is_unmatched_even_if_pilot_ranking_valid(self):
        tree,store=records(changed_reference=True)
        out=audit_archive_bytes(DAY,tree,fake_fetch(store),repository=REPO)
        self.assertEqual(out["t2_payload_valid_count"],1)
        self.assertEqual(out["t2_reference_matched_count"],0)
        self.assertEqual(out["t2_reference_unmatched_count"],1)
    def test_twelve_missing_makes_t2_unlinked_not_new_certified_forecast(self):
        tree,store=records(include_t12=False)
        out=audit_archive_bytes(DAY,tree,fake_fetch(store),repository=REPO)
        self.assertEqual(out["t2_payload_valid_count"],1)
        self.assertEqual(out["t2_reference_unmatched_count"],1)
    def test_changed_blob_sha_is_rejected(self):
        tree,store=records(corrupt_sha=True)
        # Deliberately supply original bytes under a different claimed hash.
        orig=next(iter(store.values()))
        store["f"*40]=orig
        out=audit_archive_bytes(DAY,tree,fake_fetch(store),repository=REPO)
        self.assertEqual(out["invalid_blob_or_payload_count"],1)
        self.assertEqual(out["t2_payload_valid_count"],0)
    def test_archive_with_false_local_receipt_is_rejected(self):
        x=sample()
        x["source_receipts"][0]["received_at"]="2026-11-03T18:33:00+09:00"
        pair=blob(raw(x),f"waku10/{DAY}/{CODE}.json")
        out=audit_archive_bytes(DAY,[pair[0]],fake_fetch({pair[0]["sha"]:pair[1]}),
                                repository=REPO)
        self.assertEqual(out["invalid_blob_or_payload_count"],1)
        self.assertEqual(out["t2_payload_valid_count"],0)
    def test_missing_git_blob_metadata_never_marked_valid(self):
        out=audit_archive_bytes(DAY,[{"type":"blob",
             "path":f"t12_baselines/{DAY}/{CODE}.json"}],
             lambda route:self.fail("must not fetch unidentified blob"),repository=REPO)
        self.assertEqual(out["invalid_blob_or_payload_count"],1)
        self.assertEqual(out["blob_sha_and_internal_payload_valid_count"],0)
    def test_probe_and_wrong_day_do_not_enter(self):
        tree,store=records()
        tree.append({"type":"blob","path":"operations/entry-course-write-access-v1.json"})
        tree.append({"type":"blob","path":"waku10/20261102/202611020708.json"})
        out=audit_archive_bytes(DAY,tree,fake_fetch(store),repository=REPO)
        self.assertEqual(out["blob_sha_and_internal_payload_valid_count"],2)
if __name__=="__main__":unittest.main()
