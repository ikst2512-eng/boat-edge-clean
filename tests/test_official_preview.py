import copy
import hashlib
import json
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from official_preview import preview

CODE = '202611040111'
DEADLINE = datetime.fromisoformat('2026-11-04T20:03:00+09:00')
NOW = datetime.fromisoformat('2026-11-04T19:39:21+09:00')
RAW = (Path(__file__).parent/'fixtures'/'official_preview_202611040111.json').read_bytes()
PAYLOAD = json.loads(RAW)
RACERS = [{'lane':int(r['teino']),'registration_no':r['racerno']} for r in PAYLOAD['maindata']['teiinfolist']]


class OfficialPreviewTests(unittest.TestCase):
    def call(self, payload=None, **kwargs):
        raw = RAW if payload is None else json.dumps(payload).encode()
        return preview(CODE, DEADLINE, RACERS, fetch=lambda url:raw, clock=lambda:NOW, **kwargs)

    def test_real_official_six_boats_and_start_exhibition(self):
        data, audit = self.call()
        self.assertEqual(audit['status'], 'ok')
        self.assertEqual(audit['sha256'], hashlib.sha256(RAW).hexdigest())
        self.assertEqual(len(data['racers']), 6)
        self.assertEqual(len(data['start_exhibition']), 6)
        self.assertEqual(data['start_exhibition'][0]['st'], 'F.01')
        self.assertFalse(audit['formal_t12_certified'])
        self.assertEqual(audit['fetched_at'], NOW.isoformat())

    def test_wrong_race_day_venue_number_deadline_and_registration_rejected(self):
        for key,value in [('hd','20261105'),('jcd','24'),('rno',12),('deadline','20:04')]:
            p=copy.deepcopy(PAYLOAD);p['maindata'][key]=value
            with self.subTest(field=key):self.assertIsNone(self.call(p)[0])
        p=copy.deepcopy(PAYLOAD);p['maindata']['teiinfolist'][0]['racerno']='9999'
        self.assertIsNone(self.call(p)[0])

    def test_partial_absent_invalid_measurement_and_duplicate_course_rejected(self):
        for field,value in [('extime',''),('extime','9.99'),('tilt','4'),('tilt',True),('absentflag',1)]:
            p=copy.deepcopy(PAYLOAD);p['maindata']['teiinfolist'][0][field]=value
            with self.subTest(field=field,value=value):self.assertIsNone(self.call(p)[0])
        p=copy.deepcopy(PAYLOAD);p['maindata']['sttenjiinfolist'][0]['cs']=2
        self.assertIsNone(self.call(p)[0])
        p=copy.deepcopy(PAYLOAD);p['maindata']['sttenjiinfolist'][0]['st']=''
        self.assertIsNone(self.call(p)[0])

    def test_render_start_st_matches_official_inspector_for_late_and_valid_numeric_forms(self):
        from scripts.inspect_official_beforeinfo_json import inspect
        for st in ('F.01', 'L.02', '.08', '0.08'):
            payload=copy.deepcopy(PAYLOAD)
            payload['maindata']['sttenjiinfolist'][0]['st']=st
            with self.subTest(start_st=st):
                self.assertTrue(inspect(payload)['start_exhibition_six_valid_rows'])
                data,audit=self.call(payload)
                self.assertEqual(audit['status'], 'ok')
                self.assertEqual(data['start_exhibition'][0]['st'],st)
        for st in ('', 'F01', 'L02', 'F.01x', '6.999'):
            payload=copy.deepcopy(PAYLOAD)
            payload['maindata']['sttenjiinfolist'][0]['st']=st
            with self.subTest(invalid_start_st=st):
                self.assertFalse(inspect(payload)['start_exhibition_six_valid_rows'])
                data,audit=self.call(payload)
                self.assertIsNone(data)
                self.assertNotEqual(audit['status'],'ok')

    def test_missing_official_measurements_are_audited_without_fabricating_values(self):
        p=copy.deepcopy(PAYLOAD)
        p['maindata']['teiinfolist'][0]['extime']=''
        p['maindata']['sttenjiinfolist'][0]['st']=''
        data,audit=self.call(p)
        self.assertIsNone(data)
        self.assertEqual(audit['status'],'not_published_or_unavailable')
        self.assertEqual(audit['reason'],'incomplete_official_exhibition')
        self.assertEqual(audit['missing_official_fields'],['exhibition_time','start_exhibition'])
        self.assertEqual(audit['official_measurement_counts']['exhibition_time'],5)
        self.assertFalse(audit['official_measurement_counts']['start_valid_six'])
        self.assertFalse(audit['formal_t12_certified'])

    def test_arrival_at_cutoff_cannot_be_published(self):
        ticks=iter([NOW,DEADLINE])
        data,audit=preview(CODE,DEADLINE,RACERS,fetch=lambda url:RAW,clock=lambda:next(ticks))
        self.assertIsNone(data)
        self.assertEqual(audit['reason'],'receipt_not_before_deadline')

    def test_network_outage_keeps_preview_unavailable(self):
        def fail(url):raise TimeoutError('timeout')
        data,audit=preview(CODE,DEADLINE,RACERS,fetch=fail,clock=lambda:NOW)
        self.assertIsNone(data)
        self.assertEqual(audit['status'],'not_published_or_unavailable')

    def test_redirect_and_non_200_cannot_supply_official_evidence(self):
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def geturl(self):return 'https://example.test/wrong'
            def read(self,n):return RAW
        with patch('official_preview.urlopen',return_value=Response()):
            data,audit=preview(CODE,DEADLINE,RACERS,clock=lambda:NOW)
        self.assertIsNone(data)
        self.assertEqual(audit['reason'],'unexpected_official_response')

class OfficialPreviewIntegrationTests(unittest.TestCase):
    def test_fallback_only_when_csv_missing_and_never_for_closed_race(self):
        import clean_racecard
        titles=[{'レースコード':CODE,'電話投票締切予定':'20:03'}]
        card={'レースコード':CODE}
        for racer in RACERS:
            i=racer['lane'];card[f'艇{i}_登録番号']=racer['registration_no']
        def rows(url):return (titles if '/title/' in url else [card],NOW,'a'*64)
        good, audit=preview(CODE,DEADLINE,RACERS,fetch=lambda url:RAW,clock=lambda:NOW)
        for closed,csv,expected_calls in [(False,None,1),(False,good,0),(True,None,0)]:
            with self.subTest(closed=closed,csv=csv is not None), patch.object(
                clean_racecard,'read_rows',side_effect=rows), patch.object(
                clean_racecard,'_race_read_only',return_value=closed), patch.object(
                clean_racecard,'_fetch_preview',return_value=(csv,{'status':'ok' if csv else 'not_published_or_unavailable'})), patch(
                'official_preview.preview',return_value=(good,audit)) as official:
                result=clean_racecard.racecard(CODE[:8],'01','11')
                self.assertEqual(official.call_count,expected_calls)
                self.assertEqual(len(result['racers']),6)
                self.assertEqual(result['beforeinfo'] is None,closed)

    def test_failed_official_fallback_preserves_card_and_csv_reason(self):
        import clean_racecard
        card={'レースコード':CODE,**{f"艇{r['lane']}_登録番号":r['registration_no'] for r in RACERS}}
        def rows(url):return ([{'レースコード':CODE,'電話投票締切予定':'20:03'}] if '/title/' in url else [card],NOW,'a'*64)
        with patch.object(clean_racecard,'read_rows',side_effect=rows), patch.object(
            clean_racecard,'_race_read_only',return_value=False), patch.object(
            clean_racecard,'_fetch_preview',return_value=(None,{'status':'not_published_or_unavailable'})), patch(
            'official_preview.preview',return_value=(None,{'status':'not_published_or_unavailable','reason':'TimeoutError'})):
            result=clean_racecard.racecard(CODE[:8],'01','11')
        self.assertEqual(len(result['racers']),6)
        self.assertIsNone(result['beforeinfo'])
        self.assertEqual(result['source_audit']['beforeinfo']['official_fallback']['reason'],'TimeoutError')
