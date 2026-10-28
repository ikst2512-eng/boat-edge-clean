import hashlib, importlib.util, json, sys, tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]/'scripts'/'deadline_v9'
sys.path.insert(0,str(HERE))
from classify_pages import classify
JST=timezone(timedelta(hours=9))
class Classification(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.day=datetime.now(JST).strftime('%Y%m%d')
        self.report={'date_jst':self.day,'results_seen':False,'formal_eligible':False,'errors':[],'captures':[]}
    def add(self,venue,html,clock='09:00',rno=1):
        raw=html.encode('utf8');sha=hashlib.sha256(raw).hexdigest()
        folder=self.root/'snapshots'/self.day/venue;folder.mkdir(parents=True,exist_ok=True)
        (folder/(sha+'.html')).write_bytes(raw)
        url=f'https://www.boatrace.jp/owpc/pc/race/racelist?hd={self.day}&jcd={venue}&rno={rno}'
        self.report['captures'].append({'venue_code':venue,'race_number_requested':rno,'sha256':sha,
          'bytes':len(raw),'source_url':url,'final_url':url,'formal_eligible':False,'race_deadlines_verified':False,
          'capture_started_at_jst':f'{self.day[:4]}-{self.day[4:6]}-{self.day[6:]}T{clock}:00+09:00',
          'capture_finished_at_jst':f'{self.day[:4]}-{self.day[4:6]}-{self.day[6:]}T{clock}:00+09:00'})
    def runcheck(self):
        p=self.root/'report.json';p.write_text(json.dumps(self.report))
        return classify(self.root,p)
    @staticmethod
    def table(first='10:00'):
        times=[first]+[f'{11+i//60:02d}:{i%60:02d}' for i in range(11)]
        return '<table><tr><th>締切予定時刻</th>'+''.join(f'<td>{x}</td>' for x in times)+'</tr></table>'
    def test_three_categories_and_formal_lock(self):
        self.add('01','<html><p>データがありません。</p></html>')
        self.add('02',self.table(),'09:30')
        self.add('03',self.table(),'10:30')
        r=self.runcheck()
        self.assertEqual(r['counts'],{'NO_RACE_DATA':1,'NOT_PRE_DEADLINE':1,'PRE_DEADLINE_CANDIDATE_RESEARCH_ONLY':1})
        self.assertFalse(r['formal_eligible']);self.assertEqual(r['unlock'],'LOCKED')
    def test_ambiguous_deadlines_locked(self):
        self.add('01','<html><table><tr><td>締切予定時刻</td><td>10:00</td></tr></table></html>')
        self.assertEqual(self.runcheck()['counts'],{'DEADLINE_PARSE_UNVERIFIED':1})
    def test_integrity_failure_locked(self):
        self.add('01',self.table())
        p=next((self.root/'snapshots').rglob('*.html'));p.write_text('corrupt')
        self.assertEqual(self.runcheck()['counts'],{'INTEGRITY_UNVERIFIED':1})
if __name__=='__main__':unittest.main()
