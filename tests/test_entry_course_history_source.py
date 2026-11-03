import csv
import io
import unittest
from datetime import datetime, timedelta, timezone
from entry_course_history_source import load_asof_history, BASE
JST=timezone(timedelta(hours=9))
CUTOFF='2026-11-03T19:08:00+09:00'

def csv_bytes(rows):
    stream=io.StringIO()
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig')

def fixture(day='20261102'):
    code=day+'0701'
    card={'レースコード':code,**{f'艇{i}_登録番号':str(4000+i) for i in range(1,7)}}
    result={'レースコード':code,'取得日時':'2026-11-02T16:00:00+09:00','決まり手':'逃げ'}
    for i in range(1,7):
        result[f'{i}着_艇番']=str(i)
        result[f'{i}コース_艇番']=str(i)
        result[f'{i}コース_スタートタイミング']='0.15'
    return csv_bytes([card]),csv_bytes([result])

class SourceTests(unittest.TestCase):
    def test_pairing_day_and_receipts(self):
        card,result=fixture()
        sources={BASE+'programs/race_cards/2026/11/02.csv':card,
                 BASE+'results/realtime/2026/11/02.csv':result}
        got=load_asof_history('20261103',CUTOFF,lookback_days=1,
                              fetch=lambda u:sources[u],clock=lambda:datetime(2026,11,3,18,0,tzinfo=JST))
        self.assertEqual(len(got['history']),1)
        self.assertEqual(got['history'][0]['race_card']['艇1_登録番号'],'4001')
        self.assertEqual(len(got['history'][0]['card_sha256']),64)
        self.assertEqual(got['failed_sources'],[])
    def test_cutoff_rejects_late_download(self):
        with self.assertRaisesRegex(ValueError,'not_acquired_before_cutoff'):
            load_asof_history('20261103',CUTOFF,lookback_days=1,
                              fetch=lambda u:b'',clock=lambda:datetime(2026,11,3,19,9,tzinfo=JST))
    def test_lookback_bounded(self):
        with self.assertRaisesRegex(ValueError,'invalid_cutoff_or_lookback'):
            load_asof_history('20261103',CUTOFF,lookback_days=32)
    def test_missing_source_is_visible_not_synthetic(self):
        card,result=fixture()
        got=load_asof_history('20261103',CUTOFF,lookback_days=1,
                              fetch=lambda url:card if 'race_cards' in url else (_ for _ in ()).throw(OSError('no result')),
                              clock=lambda:datetime(2026,11,3,18,0,tzinfo=JST))
        self.assertEqual(got['history'],[])
        self.assertEqual(got['failed_sources'][0]['kind'],'result')
    def test_duplicate_result_not_joined(self):
        card,result=fixture()
        first=list(csv.DictReader(io.StringIO(result.decode('utf-8-sig'))))[0]
        result=csv_bytes([first,first])
        sources={BASE+'programs/race_cards/2026/11/02.csv':card,
                 BASE+'results/realtime/2026/11/02.csv':result}
        got=load_asof_history('20261103',CUTOFF,lookback_days=1,
                              fetch=lambda u:sources[u],clock=lambda:datetime(2026,11,3,18,0,tzinfo=JST))
        self.assertEqual(got['history'],[])
    def test_cutoff_crossed_during_fetch_is_rejected(self):
        card,_=fixture()
        with self.assertRaisesRegex(ValueError,'not_acquired_before_cutoff'):
            load_asof_history('20261103',CUTOFF,lookback_days=1,
                              fetch=lambda url:card,
                              clock=iter([datetime(2026,11,3,19,7,tzinfo=JST),
                                          datetime(2026,11,3,19,9,tzinfo=JST)]).__next__)
if __name__=='__main__':unittest.main()
