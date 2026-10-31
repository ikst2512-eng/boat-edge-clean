// Regression checks for the exact production validators in index.html.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('index.html','utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script,'inline application script must exist');
new vm.Script(script,{filename:'index.html'});
function extract(name){
 const line=script.split('\n').find(l=>l.startsWith('function '+name+'('));
 assert.ok(line,'production validator '+name+' missing');
 return vm.runInNewContext(line+';'+name,{URL});
}
const classify=extract('classifyPredictionMatch'),official=extract('isOfficialResultSource');
const ticketFns=vm.runInNewContext([script.match(/const validTicket=[^\n]+/)[0],script.split('\n').find(l=>l.startsWith('function verifiedTicketArray(')),'({validTicket,verifiedTicketArray})'].join('\n'));
const validTicket=ticketFns.validTicket,verifiedTickets=ticketFns.verifiedTicketArray;
const allTen=['1-2-3','1-2-4','1-2-5','1-2-6','1-3-2','1-3-4','1-3-5','1-3-6','1-4-2','1-4-3'];
assert.equal(verifiedTickets(allTen),true);
assert.equal(verifiedTickets(allTen.slice(0,9)),false);
assert.equal(verifiedTickets([...allTen.slice(0,9),allTen[0]]),false);
for(const invalid of ['1-1-2','0-1-2','1-7-2','1-2','1-2-3-4'])assert.equal(validTicket(invalid),false,invalid);
const tickets=['1-2-3','1-3-2','2-1-3','2-3-1','3-1-2','3-2-1','1-2-4','1-4-2','2-1-4','2-4-1'];
for(const [rank,expected] of [[1,[true,true,true]],[3,[true,true,true]],[4,[false,true,true]],[5,[false,true,true]],[6,[false,false,true]],[10,[false,false,true]],[0,[false,false,false]]]){
 const r=classify(tickets,rank?tickets[rank-1]:'6-5-4');
 assert.equal(r.rank,rank);
 assert.deepEqual([r.top3,r.top5,r.top10],expected);
}
assert.equal(classify(tickets,'1-2-5').rank,0);
// Stored 2026-10-23 prediction ticket order compared with confirmed results.
// This tests comparison only, NOT first-Git-add proof or formal scoring.
for(const sample of [
 {key:'20261023-04-10',combo:'1-2-5',rank:0,tickets:['1-2-6','1-6-2','1-2-3','1-2-4','1-4-2','2-1-6','2-1-4','2-1-3','2-6-1','6-1-2']},
 {key:'20261023-06-10',combo:'3-1-2',rank:0,tickets:['1-4-6','1-6-4','1-6-5','1-5-6','1-4-5','6-1-4','4-1-6','4-1-5','6-1-5','6-4-1']},
 {key:'20261023-11-11',combo:'1-3-2',rank:4,tickets:['1-3-4','1-4-3','1-3-6','1-3-2','1-2-3','3-1-4','3-1-6','3-1-2','4-1-3','3-4-1']}
]){
 const verdict=classify(sample.tickets,sample.combo);
 assert.equal(verdict.rank,sample.rank,sample.key);
 assert.equal(verdict.top3,false,sample.key);
 assert.equal(verdict.top5,sample.rank===4,sample.key);
 assert.equal(verdict.top10,sample.rank===4,sample.key);
}
const resultValidator=vm.runInNewContext([
 script.split('\n').find(l=>l.startsWith('function isOfficialResultSource(')),
 script.split('\n').find(l=>l.startsWith('function isVerifiedResult(')),
 'isVerifiedResult'
].join('\n'),{URL});
const now=Date.parse('2026-10-23T18:00:00+09:00');
const validResult={schema_version:'boat-edge-site-result-v109',race_key:'20261023-04-10',status:'confirmed',finish_order:[1,2,5],trifecta:'1-2-5',trifecta_payout_yen_per_100:1500,fetched_at:'2026-10-23T15:30:00+09:00',source:'https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261023&jcd=04&rno=10'};
assert.equal(resultValidator(validResult,'20261023-04-10',now),true);
assert.equal(resultValidator(validResult,'20261023-04-10',now,'15:14'),true);
assert.equal(resultValidator({...validResult,fetched_at:'2026-10-23T15:13:59+09:00'},'20261023-04-10',now,'15:14'),false);
assert.equal(resultValidator(validResult,'20261023-04-10',now,'invalid'),false);
for(const patch of [
 {finish_order:[1,1,5]},{finish_order:[1,2,7]},{trifecta:'1-5-2'},
 {trifecta_payout_yen_per_100:-100},{trifecta_payout_yen_per_100:'1500'},
 {fetched_at:'2026-10-22T14:00:00Z'},{fetched_at:'2026-10-24T00:00:00+09:00'},
 {source:validResult.source+'&jcd=05'},{race_key:'20261023-04-11'},
 {status:'provisional'},{schema_version:'unverified'}
])assert.equal(resultValidator({...validResult,...patch},'20261023-04-10',now),false,JSON.stringify(patch));
const key='20261023-04-10';
const base='https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261023&jcd=04&rno=10';
assert.equal(official(base,key),true);
for(const source of [
 base.replace('https:','http:'),base.replace('www.boatrace.jp','www.boatrace.jp.evil.test'),
 base.replace('hd=20261023','hd=20261024'),base.replace('jcd=04','jcd=05'),
 base.replace('rno=10','rno=11'),base+'&rno=11',base+'&hd=20261024',base.replace('raceresult','racelist'),
 'https://example.com','not-a-url'
])assert.equal(official(source,key),false,source);
for(const literal of ['FIRST_ADD_UNCONFIRMED','SNAPSHOT_CHANGED_SINCE_FIRST_ADD','FREEZE_TIME_NOT_PROVEN','results_seen!==false','unlock!==false','scoring!==false'])assert.ok(script.includes(literal),'missing proof guard: '+literal);
assert.equal((html.match(/id="venues"/g)||[]).length,1);
const venueDeclaration=script.match(/const names=\[([^\]]+)\]/);
assert.ok(venueDeclaration,'24 venue names must be declared');
const venues=venueDeclaration[1].split(',').map(s=>s.trim().replace(/^'|'$/g,''));
assert.equal(venues.length,24,'all 24 venues must be present');
assert.equal(new Set(venues).size,24,'venue names must be unique');
assert.equal(venues[0],'桐生');
assert.equal(venues[23],'大村');
// Every statically referenced element must exist, and HTML IDs must not collide.
const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
assert.equal(new Set(ids).size,ids.length,'duplicate HTML element ID');
for(const match of script.matchAll(/getElementById\('([^']+)'\)/g)){
 assert.ok(ids.includes(match[1]),'missing HTML element #'+match[1]);
}
assert.ok(script.includes("if(activeView==='card'||activeView==='exhibit')loadRaceData(true);else if(activeView==='forecast'"),'active card and exhibition must refresh on timer');
const mergeBlock=script.slice(script.indexOf('function mergeVerifiedRaceSnapshots('),script.indexOf('\nlet displayedRaceKey=',script.indexOf('function mergeVerifiedRaceSnapshots(')));
assert.ok(mergeBlock.startsWith('function mergeVerifiedRaceSnapshots('),'missing production merger');
const merge=vm.runInNewContext(mergeBlock+';mergeVerifiedRaceSnapshots');
const snap=(card,preview,valid=true)=>({racers:[{name:'card-'+card}],beforeinfo:{racers:[{name:'preview-'+preview}]},verifiedPreview:valid,source_audit:{race_card:{fetched_at:card},beforeinfo:{fetched_at:preview}}});
const older=snap('2026-10-24T10:30:00+09:00','2026-10-24T10:36:00+09:00');
const newerCard=snap('2026-10-24T10:40:00+09:00','2026-10-24T10:32:00+09:00');
const combined=merge(older,newerCard);
assert.equal(combined.racers[0].name,'card-2026-10-24T10:40:00+09:00');
assert.equal(combined.beforeinfo.racers[0].name,'preview-2026-10-24T10:36:00+09:00');
assert.equal(combined.source_audit.beforeinfo.fetched_at,older.source_audit.beforeinfo.fetched_at);
assert.equal(merge(newerCard,older).racers[0].name,'card-2026-10-24T10:40:00+09:00');
assert.equal(merge(null,newerCard).racers[0].name,'card-2026-10-24T10:40:00+09:00');
const unverified=snap('2026-10-24T10:45:00+09:00','2026-10-24T10:46:00+09:00',false);
assert.equal(merge(older,unverified).beforeinfo.racers[0].name,'preview-2026-10-24T10:36:00+09:00');
assert.ok(script.includes('cardAt>Date.now()+300000'),'race-card timestamp in the future must be rejected');
assert.ok(script.includes('previewAt<=Date.now()+300000'),'future exhibition data must not be treated as verified');
assert.ok(html.includes('id="mobileRaceCards"'),'mobile six-lane comparison exists');
assert.ok(script.includes("mobileCards.append(card)"),'mobile cards are populated from saved racers');
assert.ok(html.includes('#raceDataSection[data-view="card"] .mobile-race-cards'),'mobile cards shown only on card tab');
assert.ok(script.includes('実進入：未取得・未検証'),'actual entry must not be silently imputed');
assert.ok(script.includes("['平均ST',txt(racer.avg_st)]"),'exhibition must show stable average ST comparison');
assert.ok(script.includes('new Set(actual).size===6'),'actual entry must contain a six-lane permutation');
assert.ok(html.includes('id="courseDataNotice"'),'course data coverage status must be visible');
assert.ok(script.includes('コース別1・2・3着率／決まり手：未取得・未検証'),'unavailable course results may not be imputed');
assert.ok(script.includes("['モーター3連率',txt(racer.motor?.trio_rate)]"),'motor trio rate included in mobile cards');
assert.ok(script.includes("['ボート3連率',txt(racer.boat?.trio_rate)]"),'boat trio rate included in mobile cards');
assert.ok(script.includes("entryAudit?.status==='ok'"),'entry must be backed by audited source');
assert.ok(script.includes('entryAt<raceDeadline'),'entry must be saved before race deadline');
assert.ok(script.includes('entryAt<=Date.now()+300000'),'entry timestamp cannot be implausibly future-dated');
assert.ok(script.includes("courseRows.length===6&&new Set(courseRows.map(r=>r.course_stats.course)).size===6"),'six unique courses required');
assert.ok(script.includes("courseAudit?.status==='ok'"),'course-specific data requires validated provenance');
assert.ok(script.includes('courseAt<courseDeadline'),'course-specific data must be collected before deadline');
assert.ok(script.includes("r.course_stats.first_rate+r.course_stats.second_rate+r.course_stats.third_rate<=100.01"),'course place percentages must have plausible sum');
assert.ok(script.includes("validCourses"),'course rates must remain gated behind validation');
assert.ok(!html.includes('class="reload-strip"'),'redundant standalone reload strip removed');
assert.ok(html.includes('id="retryPrediction"'),'refresh remains available in race navigation');
assert.ok(script.includes("document.getElementById('mobileRaceCards').replaceChildren();"),'stale mobile racers cleared when switching race');
assert.ok(script.includes("document.getElementById('courseDataNotice').replaceChildren();"),'stale course stats cleared when switching race');
assert.ok(script.includes("document.getElementById('mobileRaceCards').hidden=view!=='card'"),'exhibition view must hide redundant racer cards');
assert.ok(script.includes("document.getElementById('courseDataNotice').hidden=view!=='card'"),'course records belong only on racer card view');
assert.ok(script.includes("document.createElement('details')"),'secondary racer data must be collapsible');
assert.ok(script.includes("details.append(toggle,specs)"),'equipment details remain available on demand');
assert.ok(script.includes("racers.length!==6||new Set(racers.map(r=>r.lane)).size!==6"),'race card requires all six unique lanes');
assert.ok(script.includes("new Set(racers.map(r=>String(r.registration_no||''))).size!==6"),'race card requires six unique registration numbers');
assert.ok(script.includes("entryAudit.sha256||''"),'actual entry requires source digest');
assert.ok(html.includes('id="mobileRaceMatrix"'),'mobile six-boat comparison matrix exists');
assert.ok(html.includes('id="mobileRacerDetails"'),'full racer cards remain behind a disclosure');
assert.ok(script.includes("matrixTable.className='boat-matrix-table'"),'comparative table populated with actual data');
assert.ok(script.includes("document.getElementById('mobileRaceMatrix').replaceChildren();"),'race switch clears old comparison');
assert.ok(script.includes("document.getElementById('mobileRacerDetails').hidden=view!=='card'"),'detailed cards hidden outside racer tab');
assert.ok(html.includes('aria-label="6艇の主要成績比較・横スクロール不要"'),'comparison table must fit screen without scroll');
assert.ok(script.includes('6艇の主要情報を一覧表示'),'mobile users see the fit-to-screen guidance');
assert.ok(html.includes('.boat-matrix-table th:first-child{position:sticky;left:0'),'comparison metric label remains in view');
assert.ok(script.includes("['全国2連率',r=>displayRate(r.national?.quinella_rate)]"),'national quinella rate included in racer matrix');
assert.ok(script.includes("['当地2連率',r=>displayRate(r.local?.quinella_rate)]"),'local quinella rate included in racer matrix');
assert.ok(script.includes("['F / L',r=>String(r.F??'—')"),'F/L included in racer matrix');
assert.ok(script.includes("const weather=safePreview&&raw.beforeinfo?.weather"),'weather must be gated by audited exhibition source');
assert.ok(script.includes("typeof value==='number'&&Number.isFinite(value)&&value>=0"),'weather must not render fabricated or malformed values');
assert.ok(script.includes("water.className='exhibition-weather'"),'water observations available in exhibition view');
assert.ok(script.includes("/api/clean-racecard?hd="),'racecard must be fetched from CLEAN API');
assert.ok(!script.includes("EDGE_RAW+'/main/data/races/"),'legacy racecard fetch forbidden');
assert.ok(!script.includes("data/site_verified_entries/"),'legacy actual-entry sidecar fetch forbidden');
assert.ok(script.includes("index===0?'prediction-primary':index<3?'prediction-strong':'prediction-standard'"),'forecast tiers must be assigned from current rank');
assert.ok(script.includes("tier.textContent=index===0?'第1候補':index<3?'上位':'候補'"),'forecast tier labels must accompany colors');
assert.ok(script.includes("Object.values(predictionProbabilities).filter(Number.isFinite)"),'probability tier requires actual finite saved model values');
assert.ok(script.includes("p>=peak*0.8?'probability-high':peak>0&&p>=peak*0.45?'probability-mid'"),'probability highlights must compare within current race, not invent absolute calibration');
assert.ok(html.includes('#resultSection .comparison-hit{background:#dcf9e8'),'verified hit must be legible');
assert.ok(html.includes('#resultSection .comparison-miss{background:#fce8e8'),'verified miss must be legible');
assert.ok(script.includes("raw.race_code===code&&raw.status==='confirmed'")&&script.includes("source===expected")&&script.includes("new Set(order).size===3")&&script.includes("stamp>=confirmed"),'CLEAN result styling cannot bypass race/source/order/timestamp verification');
assert.ok(script.includes("boat-edge-clean/main/confirmed_results/")&&!script.slice(script.indexOf('async function loadResult(quiet=false){'),script.indexOf('async function loadHeldVenues')).includes("EDGE_RAW"),'result view must not fetch legacy repository');
const heldSource=script.slice(script.indexOf('async function loadHeldVenues(force=false){'),script.indexOf('function mergeVerifiedRaceSnapshots'));
assert.ok(heldSource.includes("schedule_snapshots/")&&heldSource.includes("/api/clean-schedule?date="),'historical venues must use CLEAN per-day schedule data');
assert.ok(!heldSource.includes("EDGE_RAW+'/main/data/today.json'"),'historical venue list must not read legacy today-only manifest');
assert.ok(heldSource.includes("feed.date!==dayCode"),'API schedule must match requested historical date');
assert.ok(heldSource.includes("if(token!==venueRequest||date!==s.date)return"),'stale venue request must not overwrite selected day');
assert.ok(script.includes("s.date===fmt(jst())?'本日のレース '"),'historical venue heading must show selected date');
assert.ok(html.includes('id="verificationProgress"'),'verification progress summary must be present');
assert.ok(html.includes('class="verification-modes"'),'four-mode responsive card grid must be present');
for(const label of ['的中率','回収率','的中','購入想定','払戻想定','収支','少数サンプル']){
 assert.ok(script.includes(label),'verification must display '+label);
}
assert.ok(script.includes('v.sample_races>0?number(v.actual_hit_rate_pct)'),'unverified hit rates must not be displayed');
assert.ok(script.includes('v.sample_races>0?number(v.actual_roi_pct)'),'unverified ROI must not be displayed');
assert.ok(html.includes('id="hitHistoryFilter"'),'winning-race mode filter must be visible');
assert.ok(html.includes('id="hitHistory"'),'verified winning-race list must be visible');
assert.ok(script.includes('CLEAN_VERIFIED_FOUR_MODE_HISTORY_V1'),'list must use independently verified result history');
assert.ok(script.includes("v.modes[filter]?.hit"),'per-mode wins must be filterable');
assert.ok(script.includes("Object.values(v.modes).some(m=>m.hit)"),'all-modes view must only show actual hits');
assert.ok(script.includes("winning_stake_yen"),'hit history must show staked amount on actual winning ticket');
assert.ok(script.includes("的中した方式の収支"),'hit history must show simulated net result');
assert.ok(html.includes(".prediction-row.verified-win"),'winning prediction red style must exist');
assert.ok(script.includes("review-hit-summary"),'single race answer checks must summarize only winning modes');
assert.ok(!script.includes("add(label,m.hit?"),'individual answer check must not duplicate four-mode cards');
assert.ok(html.includes('.review-hit-summary'),'verified race wins must be visually prominent');
assert.ok(script.includes("winners.length?'● 的中：'"),'verified hit summary must include mark');
assert.ok(script.includes("不的中：4パターンとも該当なし"),'verified all-mode miss must be explicit');
assert.ok(script.includes("結果待ち（不的中として集計しません）"),'pending results must not be treated as misses');
assert.ok(html.includes('id="overdueAuditRows"'),'overdue result list must be visible');
assert.ok(script.includes('CLEAN_RESULT_COLLECTION_STATUS_V1'),'only CLEAN audited result statuses are shown');
assert.ok(script.includes('未取得は不的中に含めません'),'missing results must never count as losses');
assert.ok(html.includes('id="recent30Metrics"'),'rolling 30 proof-backed metric is shown');
assert.ok(script.includes('d.recent_30?.modes?.hit'),'rolling metric uses verified summary');
assert.ok(script.includes('let fourModePerformanceRequest=0;'),'overlapping verification fetches must have a request token');
assert.ok(script.includes('if(request!==fourModePerformanceRequest||budget!==Number(document.getElementById(\'performanceBudget\').value))return;'),'outdated responses must never render cards');
assert.ok(script.includes('grid.replaceChildren();\n  const c=d.counts'),'clear four-mode cards again at the commit point');
assert.ok(html.includes('id="forecastVenue"')&&html.includes('id="forecastRace"'),'forecast has direct venue and race selectors');
assert.ok(html.includes('id="deadlineSection" hidden'),'deadline list is available on home');
assert.ok(script.includes("document.getElementById('deadlineSection').hidden=view!=='home'"),'deadline list is visible on home only');
assert.ok(script.includes("forecastVenue.addEventListener('change'"),'forecast venue selector changes race selection');
assert.ok(html.includes('横スクロール不要'),'mobile racecard label must describe fit-to-screen');
assert.ok(html.includes('min-width:0!important;max-width:100%;table-layout:fixed'),'six-lane table must fit small viewports');
assert.ok(script.includes("['チルト',r=>txt(byLane(preview,r.lane).tilt)]"),'tilt row must explicitly render');
assert.strictEqual((script.match(/\['展示タイム',r=>txt\(byLane\(preview,r\.lane\)\.exhibition_time\)\]/g)||[]).length,1,'mobile matrix exhibition time must occur once');
assert.strictEqual((script.match(/\['チルト',r=>txt\(byLane\(preview,r\.lane\)\.tilt\)\]/g)||[]).length,1,'mobile matrix tilt must occur once');
assert.ok(script.includes('直前データ収集が未実装'),'unavailable tilt must be distinguished from loading error');
assert.ok(html.includes('横スクロール不要'),'mobile racecard must be designed to fit viewport');
assert.ok(html.includes('table-layout:fixed'),'six-boat columns must fit screen');
assert.ok(script.includes("['チルト',r=>txt("),'mobile matrix must show tilt');
assert.ok(script.includes('直前データ未取得です'),'missing beforeinfo must be explicitly explained');
assert.ok(html.includes('id="resultVenue"'),'results must have a direct venue selector');
assert.ok(script.includes("resultVenue.addEventListener('change'"),'result venue selection must update selected venue');
assert.ok(script.includes("document.getElementById('resultVenue').value=String(s.venue+1)"),'result venue picker must sync with active race');
assert.ok(html.includes('#forecast .prediction-row{gap:7px;padding:7px 9px'),'forecast tickets should use compact cards');
assert.ok(script.includes("openCleanListTab(view,item.race)")&&script.includes("['AI予想','forecast']"),'result rows open their existing forecast');
assert.ok(html.includes('id="forecastResultDetail"'),'forecast must show confirmed result detail');
assert.ok(script.includes("confirmedForecastResult=order.join('-');confirmedForecastResultKey=key;drawPredictions()"),'confirmed result must refresh matching forecast ticket marks');
assert.ok(script.includes("結果一致！ ※締切前保存未確認"),'matching provisional ticket must be marked without claiming verified bet');
assert.ok(script.includes("的中確定！ 締切前予想と照合済み"),'verified winning ticket remains distinct');
assert.ok(html.includes('.prediction-row.result-matched-reference'),'reference matches must be visually emphasized');
assert.ok(script.includes("archive.predictions.indexOf(item.match)+1"),'a research list hit must match saved Top-10');
assert.ok(html.includes('.clean-race-card.verified-hit')&&script.includes("card.classList.add('verified-hit')"),'verified winning races have visible row highlight');
assert.ok(script.includes("研究上位'+item.winningRank+'点目が一致"),'research ticket rank appears on matching results');
assert.ok(script.includes('未照合は的中扱いしません'),'unverified races are never scored as hits');

 // Legacy V284 parity: a pending result is neither a verified miss nor a verified hit.
 const pendingRace='20261023-04-10';
 for(const state of ['pending','awaiting_result','provisional','unverified']){
   assert.equal(resultValidator({...validResult,status:state},pendingRace,now),false,'state '+state+' must not count as confirmed');
 }
 assert.ok(script.includes("item.hitState==='miss'?'保存済み研究10点は不的中':'研究予想の証拠照合待ち'"),'unverified research rows must remain pending');
 assert.ok(script.includes('結果未確認（不的中として集計しません）'),'unknown results must not be counted as a loss');
 assert.ok(script.includes("verified.filter(e=>e.hitState==='hit')"),'verified hit count must use explicit hit status');
 assert.ok(script.includes('研究予想の証拠照合待ち'),'pending/missing results must remain distinct from misses');
 assert.ok(script.includes("['保存済み',archived+'R'],['検証完了',completed+'R'],['結果待ち',pending+'R']"),'saved, verified and pending counts must remain distinct');
 assert.ok(script.includes('結果一致！ ※締切前保存未確認'),'reference-only winning match must disclose unproven predeadline evidence');
 assert.ok(script.includes('的中確定！ 締切前予想と照合済み'),'verified hit must be gated by predeadline evidence');
 console.log('PASS: pending results never treated as verified hits or losses; reference matches remain unverified');


 // The six-boat card and predeadline source audits must remain fail-closed.
 for (const [literal,message] of [
  ["racers.length!==6||new Set(racers.map(r=>r.lane)).size!==6",'six unique lanes'],
  ["new Set(racers.map(r=>String(r.registration_no||''))).size!==6",'six unique racer registrations'],
  ["entryAudit?.status==='ok'",'actual entry source audited'],
  ["entryAudit.sha256||''",'actual entry source digest'],
  ["entryAt<raceDeadline",'entry recorded before cutoff'],
  ["entryAt<=Date.now()+300000",'entry future-time guard'],
  ["courseRows.length===6&&new Set(courseRows.map(r=>r.course_stats.course)).size===6",'six unique course statistics'],
  ["courseAudit?.status==='ok'",'course statistics audited'],
  ["courseAt<courseDeadline",'course statistics predeadline'],
  ["r.course_stats.first_rate+r.course_stats.second_rate+r.course_stats.third_rate<=100.01",'course rate sanity check'],
  ["const weather=safePreview&&raw.beforeinfo?.weather",'weather only from audited exhibition'],
  ["typeof value==='number'&&Number.isFinite(value)&&value>=0",'reject malformed weather observations']
 ])assert.ok(script.includes(literal),'missing six-boat/provenance guard: '+message);
 console.log('PASS: six-boat completeness and immutable-source/cutoff guard presence');

for(const [literal,label] of [
  ["/^2026102803(?:0[6-9]|1[0-2])$/.test(code)",'Oct 28 Edogawa cancelled 6-12 guard'],
  ["中止・順延（江戸川6〜12R）：的中率・回収率の対象外",'cancelled races excluded from performance'],
  ["code==='202610280112'",'Oct 28 Kiryu 12 unsettled guard'],
  ["公式精算確認待ち",'unsettled trifecta clearly pending official settlement'],
  ["返還等の公式精算は未確認です",'no fabricated refund assertion']
])assert.ok(script.includes(literal),'missing unsettled-status UI guard: '+label);
console.log('PASS: cancellation and unsettled trifecta displayed without a hit/miss verdict');

console.log('PASS: JS syntax, Top3/5/10 boundaries, official URL validation, predeadline guards, 24-venue entry point');


async function testVerifiedFetchFallback(){
 const begin=script.indexOf('async function verifiedFourModeRace(key){');
 const end=script.indexOf('\nconst verifiedRaceCache=',begin);
 assert.ok(begin>=0&&end>begin,'verified fetch function extractable');
 const source=script.slice(begin,end);
 const record={schema:'CLEAN_VERIFIED_FOUR_MODE_RACE_V1',race_code:'202610282309',verified:true,simulated_only:true,budget_yen:5000,first_git_sha:'f'.repeat(40),official_finish:'5-3-6',official_payout_yen_per_100:31950,modes:Object.fromEntries(['hit','balance','hole','narrow'].map(k=>[k,{hit:false,invested_yen:5000,return_yen:0}]))};
 const ctx={validTicket,Date,atob,fetchTimed:async url=>{
  if(url.includes('raw.githubusercontent.com'))throw Error('RAW_BLOCKED');
  return {ok:true,json:async()=>({encoding:'base64',content:Buffer.from(JSON.stringify(record)).toString('base64')})};
 }};
 const fn=vm.runInNewContext(source+';verifiedFourModeRace',ctx);
 assert.equal((await fn('20261028-23-09')).official_finish,'5-3-6');
 ctx.fetchTimed=async url=>({ok:true,json:async()=>url.includes('raw.githubusercontent.com')?record:{encoding:'base64',content:Buffer.from(JSON.stringify({...record,verified:false})).toString('base64')}});
 assert.equal((await fn('20261028-23-09')).verified,true,'valid primary must not be overwritten');
 ctx.fetchTimed=async url=>{if(url.includes('raw.githubusercontent.com'))throw Error('RAW_BLOCKED');return {ok:true,json:async()=>({encoding:'base64',content:Buffer.from(JSON.stringify({...record,verified:false})).toString('base64')})}};
 await assert.rejects(fn('20261028-23-09'),/FOUR_MODE_VERIFICATION_INVALID/);
 ctx.fetchTimed=async()=>{throw Error('NETWORK_DOWN')};
 await assert.rejects(fn('20261028-23-09'),/FOUR_MODE_VERIFICATION_PENDING/);
 console.log('PASS: verified race fallback, strict proof rejection, primary precedence and double-outage pending');
}
testVerifiedFetchFallback().catch(error=>{console.error(error);process.exitCode=1});

assert.ok(!html.includes('本命（旧方式）'),'forecast must not offer old main mode');
assert.ok(!html.includes('predictionModes.research={...confirmed.modes.hit'),'research must not copy old main tickets');
console.log('PASS: forecast top-ten is not filled from old four-mode main picks');

assert.equal((html.match(/<\/script>/g)||[]).length,1,'only one script closing tag is allowed');
assert.ok(/<\/script><\/body><\/html>\s*$/.test(html),'no raw source may follow HTML close');
console.log('PASS: no appended source code visible after HTML');

// Reject the exact stale legacy screenshot on all future builds.
const forecastMarkup=html.match(/<section class="box" id="forecast">([\s\S]*?)<section class="box" id="resultSection"/)?.[1];
assert.ok(forecastMarkup,'forecast section must exist');
for(const stale of ['旧4パターンの比較検証を表示','目標的中率：本命60%','data-mode="hit"'])assert.ok(!forecastMarkup.includes(stale),'stale legacy forecast UI forbidden: '+stale);
assert.ok(html.includes('data-clean-forecast-ui="research-only-20261030"'),'forecast UI revision marker required');
console.log('PASS: stale legacy forecast markup blocked');

assert.ok(!html.includes('async function cleanFourModeForecast('),'old forecast API removed');
assert.ok(!html.includes('async function loadVerifiedForecastForDisplay('),'old forecast override removed');
const forecastLoader=script.slice(script.indexOf('async function loadPredictions('),script.indexOf(';let reviewSequence=0;'));
assert.ok(forecastLoader.startsWith('async function loadPredictions('),'forecast loader must remain present');
assert.ok(forecastLoader.includes("response.status===404"),'missing archive must trigger fallback');
assert.ok(forecastLoader.includes("fetchTimed('https://boat-edge-clean.onrender.com/api/predictions?hd='"),'fallback must call CLEAN research API');
assert.ok(forecastLoader.includes('main/research_snapshots/'),'archived research fallback must exist');
assert.ok(forecastLoader.indexOf('main/research_snapshots/')<forecastLoader.indexOf('/api/predictions?hd='),'read existing research archive before live API');
assert.ok(forecastLoader.includes("saved.race_code!==key.replaceAll('-','')"),'saved research must belong to selected race');
assert.ok(forecastLoader.includes("saved.status!=='research'")&&forecastLoader.includes("saved.validated!==false"),'saved research cannot be labeled formal');
assert.ok(forecastLoader.includes("created>=cutoff"),'reject post-cutoff saved research');
assert.ok(forecastLoader.includes("saved.predictions.length!==10"),'saved research requires exactly ten tickets');
assert.ok(forecastLoader.includes("new Set(saved.predictions).size!==10"),'reject duplicate saved research tickets');
assert.ok(forecastLoader.includes("fresh.status!=='research'"),'never present other API modes as research');
assert.ok(forecastLoader.includes("fresh.validated!==false"),'fallback must remain visibly exploratory');
assert.ok(forecastLoader.includes("fresh.predictions.length!==10"),'fallback must require exact ten picks');
assert.ok(forecastLoader.includes("new Set(fresh.predictions).size!==10"),'fallback must reject duplicate tickets');
assert.ok(forecastLoader.includes("if(token!==window.predictionRequestId||sameRaceKey()!==key)return;"),'reject stale race response');
console.log('PASS: archived prediction 404 fallback guard and research-only validation');
assert.ok(html.includes("throw Error('PREDICTION_NOT_PUBLISHED')"),'missing saved research must fail closed');

assert.ok(!html.includes('<nav class="view-tabs"'),'duplicate top view tabs removed');
assert.ok(html.indexOf('id="resultList"')>html.indexOf('id="forecast"') && html.indexOf('id="resultList"')<html.indexOf('id="resultSection"'),'race list must appear under forecasts');
assert.ok(script.includes("main/prospective_predictions/"),'forecast race cards must compare archived Top-10');
assert.ok(script.includes("研究10点的中"),'race cards must label research hits');
assert.ok(script.includes("500円仮定の払戻"),'race cards must display simulated payout');
console.log('PASS: race cards in forecast; no redundant tabs; research hit payouts');

assert.ok(!script.includes("record.official_finish!==item.match"),'old four-mode list verification must not return');
assert.ok(!script.includes("document.querySelector('.view-tabs').scrollIntoView"),'no removed-tab scroll references');

assert.ok(html.includes('id="forecastPreviewStatus"')&&html.includes('id="forecastPreviewRows"'),'forecast needs visible beforeinfo summary');
assert.ok(script.includes('async function loadForecastPreview()')&&script.includes('loadForecastPreview();loadForecastCourseStats();loadForecastPriorResults()}'),'forecast must fetch selected race beforeinfo');
assert.ok(script.includes("raw.source_audit?.beforeinfo?.status!=='ok'"),'reject unsupported preview sources');
console.log('PASS: selected-race beforeinfo panel in forecast');

// Pages review requires a real CLEAN API origin, not a Pages-relative /api path.
assert.ok(html.includes("fetchTimed('https://boat-edge-clean.onrender.com/api/clean-result?hd="),'review must fetch CLEAN result via Render');
assert.ok(!html.includes("fetchTimed('/api/clean-result?hd="),'review must not request API from GitHub Pages');

// Published Pages must fetch racecard/exhibition from the actual CLEAN API host.
assert.ok(html.includes("fetchTimed('https://boat-edge-clean.onrender.com/api/clean-racecard?hd="),'racecard must use CLEAN Render');
assert.ok(!html.includes("fetchTimed('/api/clean-racecard?hd="),'Pages-relative racecard API would return 404');

// Historical schedule fallback: an unavailable CLEAN API must not hide a past date.
const scheduleLoader=script.slice(script.indexOf('async function loadHeldVenues('),script.indexOf('function mergeVerifiedRaceSnapshots('));
assert.ok(scheduleLoader.includes("if(api?.status===404&&date>=fmt(jst()))throw Error('SCHEDULE_NOT_PUBLISHED')"),'only current/future 404 may be unavailable');
assert.ok(scheduleLoader.includes("if(date<fmt(jst()))data=await historicalHeldVenues(date)"),'historical 404 and 503 must reach results-based schedule');
assert.ok(scheduleLoader.includes("archive.status===404||(date<fmt(jst())&&archive.status>=500)"),'historical archive 5xx must try CLEAN schedule API and results CSV fallback');
assert.ok(scheduleLoader.includes("else throw Error('SCHEDULE_ARCHIVE_HTTP_'+archive.status)"),'current date must still reject unexpected archive errors');
assert.ok(scheduleLoader.indexOf("if(api?.status===404&&date>=fmt(jst()))")<scheduleLoader.indexOf("if(date<fmt(jst()))data=await historicalHeldVenues(date)"),'historical fallback ordering must be preserved');
console.log('PASS: historical schedule 404/503 fallback regression');

// GitHub Pages must ship the runtime navigation script referenced by index.html.
const pagesWorkflow=fs.readFileSync('.github/workflows/deploy-pages.yml','utf8');
assert.ok(html.includes("navScript.src='navigation.js'"),'site expects external navigation script');
assert.ok(pagesWorkflow.includes('cp index.html navigation.js public/'),'Pages must publish both runtime assets');
assert.ok(pagesWorkflow.includes('cmp -s public/navigation.js /tmp/clean-deployed-navigation.js'),'Pages must verify deployed navigation asset');
assert.ok(pagesWorkflow.includes('      - navigation.js'),'navigation changes must trigger Pages publication');
console.log('PASS: Pages navigation asset packaging and verification');

// Project-scoped GitHub Pages review links must not navigate to a missing /review route.
const navigation=fs.readFileSync('navigation.js','utf8');
assert.ok(navigation.includes("location.hostname.endsWith('.github.io')"),'restrict Pages route handling to GitHub Pages');
assert.ok(navigation.includes("target.searchParams.set('screen','review')"),'Pages review must navigate via single-page screen query');
assert.ok(navigation.includes("location.pathname.startsWith('/boat-edge-clean/')"),'Pages must restore review screen under project path');
console.log('PASS: Pages project-path review navigation regression');

// BOATERS-inspired single-page forecast must not regress to scattered panels.
const resultFirst=html.indexOf('id="forecastResultFirstStatus"');
const prediction=html.indexOf('id="predictionRows"');
const leader=html.indexOf('id="forecastLeaderRows"');
const evidence=html.indexOf('id="forecastEvidenceStatus"');
assert.ok(resultFirst>=0&&resultFirst<prediction&&prediction<leader&&leader<evidence,'result, prediction, conditional stats and preview should share one ordered page');
for(let lane=1;lane<=6;lane++)assert.ok(html.includes('data-forecast-leader="'+lane+'"'),'missing leader '+lane);
assert.ok(script.includes('function selectForecastLeader(leader)'),'leader selection must respond to interaction');
assert.ok(script.includes('forecastEvidenceMirror.observe'),'verified predeadline preview must be mirrored without an extra fetch');
assert.ok(script.includes('forecastResultMirror.observe'),'validated confirmed result must be mirrored without an extra fetch');
assert.ok(html.includes('先頭艇として選択中')&&html.includes('未取得'),'missing stats must not be fabricated as 0%');
console.log('PASS: one-page forecast layout and source-safe comparison controls');

assert.ok(script.includes("bar.setAttribute('aria-label',r.lane+'号艇の実コース別3連対率')"),'course three-place rate progress bar must be accessible');
assert.ok(script.includes('bar.max=100;bar.value=three'),'three-place rate bar must use verified percentage');

assert.ok(html.includes('id="forecastCourseStatsSource"'),'course stats must expose evidence status');
assert.ok(script.includes("対象期間・標本数は未提供"),'unavailable course-stat sample size must be disclosed');

assert.ok(script.includes('選手の直近10走と混同しない'),'course-stats coverage must not masquerade as last-ten-runs rates');

assert.ok(html.includes('id="forecastAiLeaderShares"'),'forecast must show AI first-boat Top10 comparison');
assert.ok(script.includes("selectedPredictionMode==='research'?predictionTickets.slice(0,10):[]"),'AI leader shares must exclude unrelated prediction modes');
assert.ok(script.includes('残りの買い目は含まない'),'Top10 share must not claim complete first-place probabilities');
assert.ok(script.includes('function drawPredictions(){renderForecastAiLeaderShares();renderForecastAiLeaderDetail('),'AI leader distribution must follow saved prediction updates');

assert.ok(script.includes("eligible.length===10&&new Set(eligible).size===10"),'AI leading-boat comparison must have exactly ten distinct tickets');
assert.ok(script.includes("上位10点の確率値が揃っていないため、先頭艇比較は非表示"),'incomplete probabilities cannot produce fake zero bars');
assert.ok(script.includes("total>100.01"),'invalid probability sum must be rejected');

assert.ok(html.includes('id="forecastAiLeaderDetailRows"'),'show model second/third pairs by selected leader');
assert.ok(script.includes('function renderForecastAiLeaderDetail(leader)'),'selected leader model comparison renderer required');
assert.ok(script.includes('const denominator=selected.reduce('),'second/third model relative share must use selected head denominator');
assert.ok(script.includes('実測・条件付き集計'),'distinguish empirical 2/3 rates from modeled pair share');

assert.ok(script.includes("'Top10候補外'"),'unlisted combinations must not be reported as observed zero chance');

assert.ok(script.includes('const requestId=++forecastCourseStatsRequestId'),'course-stat requests must have race switch token');
assert.ok(script.includes("requestId!==forecastCourseStatsRequestId||key!==sameRaceKey()"),'stale course stats must be discarded');

assert.ok(script.includes('実コース別成績：API取得失敗（HTTP '),'forecast must explain network HTTP failures');
assert.ok(script.includes('実コース別成績：取得元・締切前時刻・6艇の証拠を検証できません'),'forecast must distinguish verification failure');
assert.ok(script.includes('実コース別成績：通信または読み込みに失敗しました'),'forecast must explain parse failures');

assert.ok(html.includes('id="forecastPriorResultRows"'),'prior confirmed empirical rates table required');
assert.ok(script.includes('Array.from({length:race-1}'),'only earlier races may be inspected');
assert.ok(script.includes("item.race_code!==code||item.status!=='confirmed'"),'unverified result not eligible for conditional rate');
assert.ok(script.includes('renderForecastPriorResults(leader)'),'leader switch must refresh historical real data');
assert.ok(script.includes('loadForecastPriorResults()}else if(activeView'),'selected-race changes must refresh prior results');

assert.ok(script.includes('取得不足のため当日傾向として扱わない'),'partial earlier-race collection must warn of incomplete daily coverage');

assert.ok(script.includes('priorResultExpected>0&&priorRaceResults.length===priorResultExpected'),'conditional actual rates require complete prior-race coverage');
assert.ok(script.includes("'集計不足'"),'partial prior results must suppress rather than calculate observed percentages');

assert.ok(script.includes('complete&&n>=3?'),'conditional historical percentages require at least three head-specific samples');
assert.ok(script.includes('標本3件未満'),'small samples must show counts rather than percent');

assert.ok(script.includes('let priorResultRequestId=0,priorRaceResults=[],priorResultExpected=0;'),'prior-result render must initialize expected count before first use');

assert.ok(script.includes("!/^[0-9]{8}$/.test(date)||!/^[0-9]{2}$/.test(venue)"),'historical result lookup must reject malformed date or venue');

assert.ok(html.includes('締切前に取得済みだった証明はない'),'retrospective confirmed results must not imply pre-deadline availability');
assert.ok(script.includes('Date.parse(item.confirmed_at_jst)'),'retrospective results require evidence acquisition timestamp');

assert.ok(script.includes('Date.parse(item.confirmed_at_jst)>Date.now()||Date.parse(item.collected_at_jst)>Date.now()'),'future-dated result evidence must not be counted as confirmed history');

assert.ok(script.includes('Date.parse(item.collected_at_jst)<Date.parse(item.confirmed_at_jst)'),'historical evidence cannot precede confirmation');

assert.ok(html.includes('confirmed_at_jstは公式の着順確定時刻ではなく結果ソースの取得時刻'),'retrospective statistics must disclose timestamp provenance');

// Archived prospective candidates are loaded directly from GitHub, bypassing
// the server API: their displayed timestamp provenance must be checked too.
assert.ok(script.includes("const receiptOrderVerified=Number.isFinite(generatedAt)"),'archived forecast UI must verify timestamp ordering');
assert.ok(script.includes("titleReceived<=generatedAt&&cardsReceived<=generatedAt"),'both source receipts must precede generation');
assert.ok(script.includes("時刻証拠未検証：元データの受信時刻が生成時刻より後"),'uncertain archive evidence must be explained in the visible forecast');

assert.ok(script.includes("fresh.provenance_warning==='SOURCE_RECEIPT_ORDER_UNVERIFIED'"),'fallback forecast must propagate API provenance warning');
assert.ok(script.includes('研究予想API：元データ受信順序・時刻証拠が未検証です'),'fallback API warning must be visible');

const pagesWorkflow=fs.readFileSync('.github/workflows/deploy-pages.yml','utf8');
assert.ok(pagesWorkflow.includes('DEPLOYED_ARCHIVED_RESULT_PASS 202610270101 3-4-1'),'published browser test must verify a real archived race result');
assert.ok(pagesWorkflow.includes("#resultDetail .result-combo .boat-num"),'published browser test must inspect actual three boat numbers');
