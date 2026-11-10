// Regression checks for the exact production validators in index.html.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('index.html','utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script,'inline application script must exist');
// The header exposes exactly one daily-candidate entry, never fake per-race tabs.
assert.equal((html.match(/class="header-candidate-tab"/g)||[]).length,1);
assert.ok(html.includes('class="header-candidate-tab" href="/selection"'));
assert.ok(html.includes('>候補レース</a>'));
assert.ok(!html.includes('href="/selection">購入候補</a>'),'avoid duplicate candidate navigation');
// Candidate destination must not promote historical verified comparisons to today's tips.
const candidateHtml=fs.readFileSync('selection.html','utf8');
assert.ok(candidateHtml.includes('id="todayCandidateRaces"'));
assert.ok(candidateHtml.includes('id="todayCandidateDate"'));
assert.ok(candidateHtml.includes("timeZone:'Asia/Tokyo'"));
assert.ok(candidateHtml.includes('過去の確定結果から作った研究候補を、本日の購入候補として表示することはありません。'));

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
// Exercise the real official-exhibition missing-data explanation, not a test-only copy.
const gapStart=script.indexOf('function explainOfficialPreviewGap(');
const gapEnd=script.indexOf('\nfunction mergeVerifiedRaceSnapshots(',gapStart);
assert.ok(gapStart>=0&&gapEnd>gapStart,'missing public official field-level diagnosis');
const explainGap=vm.runInNewContext(script.slice(gapStart,gapEnd)+';explainOfficialPreviewGap');
const partialOfficial={
 official_fallback:{
  reason:'incomplete_official_exhibition',
  official_measurement_counts:{racers:6,exhibition_time:5,tilt:6,start_rows:6,start_valid_six:false},
  missing_official_fields:['exhibition_time','start_exhibition']
 }
};
assert.match(explainGap(partialOfficial),/展示タイム 5\/6艇/);
assert.match(explainGap(partialOfficial),/チルト 6\/6艇/);
assert.match(explainGap(partialOfficial),/スタート展示 未検証（6\/6行受信）/);
assert.match(explainGap(partialOfficial),/推測値は表示しません/);
assert.match(explainGap({official_fallback:{reason:'official_racer_or_absence_mismatch'}}),/登録番号または欠場情報/);
assert.match(explainGap({official_fallback:{reason:'official_race_or_deadline_mismatch'}}),/対象レース・締切時刻/);
assert.match(explainGap({official_fallback:{reason:'receipt_not_before_deadline'}}),/締切前の取得完了を確認できない/);
assert.match(explainGap({official_fallback:{reason:'incomplete_official_exhibition',
 official_measurement_counts:{exhibition_time:7,tilt:6,start_rows:6,start_valid_six:false},
 missing_official_fields:['exhibition_time']}}),/未取得／公開待ち／取得記録の検証待ち/);
assert.match(explainGap({status:'not_verified_historical'}),/未取得／公開待ち／取得記録の検証待ち/);
assert.ok(script.includes('explainOfficialPreviewGap(raw.source_audit?.beforeinfo)'),'exhibition tab must use audited missing-data diagnosis');
// Real published racecard failure states must not conflate a transient Render
// failure with a missing race or source-validation mismatch.
const errorStart=script.indexOf('function racecardFailureMessage(');
const errorEnd=script.indexOf('async function loadRaceData(',errorStart);
assert.ok(errorStart>=0&&errorEnd>errorStart,'published racecard failure formatter missing');
const failureText=vm.runInNewContext(script.slice(errorStart,errorEnd)+';racecardFailureMessage');
for(const code of ['HTTP_429','HTTP_500','HTTP_502','HTTP_503','HTTP_504','TimeoutError','RACECARD_TRANSPORT_UNAVAILABLE']){
 assert.match(failureText(code),/公開APIに一時的に接続できません/,code);
 assert.match(failureText(code),/未取得の6艇情報は表示しません/,code);
}
assert.match(failureText('HTTP_404'),/未配信/);
assert.doesNotMatch(failureText('HTTP_404'),/一時的に接続できません/);
assert.match(failureText('HTTP_422'),/締切済み/);
for(const reason of ['PRE_RACE_SOURCE_NOT_VERIFIED','INCOMPLETE_OR_DUPLICATE_RACE_CARD','INCOMPLETE_RACE_CARD'])
 assert.match(failureText(reason),/検証に失敗/,reason);
assert.match(failureText('CARD_EVIDENCE_INVALID'),/取得時刻や締切情報/);
assert.match(failureText('something unexpected'),/内容または通信を検証できません/);
assert.ok(script.includes('status.textContent=racecardFailureMessage('),'display must use tested failure mapping');
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
assert.ok(script.includes('対象レースの締切前6艇分の取得記録を検証できていません。'),'unverified exhibition values must be distinguished from transport failure or an unimplemented collector');
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
assert.ok(script.includes('async function loadForecastPreview()')&&script.includes('loadForecastCourseStats();loadForecastPriorResults();loadForecastPreview()'),'racecard rates subtab must fetch verified beforeinfo and course statistics');
assert.ok(script.includes("raw.source_audit?.beforeinfo?.status!=='ok'"),'reject unsupported preview sources');
console.log('PASS: verified selected-race beforeinfo and card-level rates panel');

// Pages review requires a real CLEAN API origin, not a Pages-relative /api path.
assert.ok(html.includes("fetchTimed('https://boat-edge-clean.onrender.com/api/clean-result?hd="),'review must fetch CLEAN result via Render');
assert.ok(!html.includes("fetchTimed('/api/clean-result?hd="),'review must not request API from GitHub Pages');

// Published Pages must fetch racecard/exhibition from the actual CLEAN API host.
assert.ok(html.includes("fetchTimed('https://boat-edge-clean.onrender.com/api/clean-racecard?hd="),'racecard must use CLEAN Render');
assert.ok(!html.includes("fetchTimed('/api/clean-racecard?hd="),'Pages-relative racecard API would return 404');
assert.ok(script.includes('await loadHeldVenues();'),'racecard loading must wait for the verified daily schedule');
assert.ok(script.includes('todayVenueRaces.partial_coverage!==true'),'partial frozen schedules must not prove a race is absent');
assert.ok(script.includes("scheduledVenue?'このレースは開催されていません':'この場は開催されていません'"),'confirmed non-held selections must stop before the racecard API');

// The published racecard must retry transient server/network errors only,
// preserving race identity and refusing 404 or 422 as retryable evidence.
const cardLoader=script.slice(script.indexOf('async function loadRaceData('),script.indexOf('async function loadRaceData(')+3500);
assert.ok(cardLoader.includes("for(let attempt=0;attempt<3;attempt++)")&&
          cardLoader.includes("[429,500,502,503,504].includes(response.status)"),
          'Racecard loader must bound retries to transient HTTP responses');
assert.ok(cardLoader.includes("if(token!==window.raceDataRequestId||key!==sameRaceKey())return;"),
          'Retrying racecards must never leak a stale selected race');
assert.ok(cardLoader.includes("if(!response.ok)throw Error('HTTP_'+response.status)"),
          'Racecard 404/422 or exhausted transient errors must still fail closed');

// Historical schedule fallback: an unavailable CLEAN API must not hide a past date.
const scheduleLoader=script.slice(script.indexOf('async function loadHeldVenues('),script.indexOf('function mergeVerifiedRaceSnapshots('));
assert.ok(scheduleLoader.includes("if(api?.status===404&&date>=fmt(jst()))throw Error('SCHEDULE_NOT_PUBLISHED')"),'only current/future 404 may be unavailable');
assert.ok(scheduleLoader.includes("if(date<fmt(jst()))data=await historicalHeldVenues(date)"),'historical 404 and 503 must reach results-based schedule');
assert.ok(scheduleLoader.includes("const pagesSchedule=location.hostname==='ikst2512-eng.github.io'")&&
          scheduleLoader.includes("for(const endpoint of [pagesSchedule,rawSchedule].filter(Boolean))")&&
          scheduleLoader.includes("const response=await fetchTimed(endpoint,{cache:'no-store'})")&&
          scheduleLoader.includes("}catch(_){/* Keep trying CLEAN sources; do not use legacy today.json. */}"),
          'same-origin Pages failure must fall back through CLEAN Raw and Render sources');
assert.ok(scheduleLoader.includes("else if(!archive?.ok){"),'all Raw archive non-2xx/network failures must reach CLEAN API, including today');
assert.ok(scheduleLoader.includes("if(archive?.ok){data=await archive.json()"),'valid archived schedule remains preferred');
assert.ok(scheduleLoader.includes('partial_coverage:feed.partial_coverage===true'),'partial fallback coverage must survive the API-to-UI transform');
assert.ok(scheduleLoader.includes("else throw Error('SCHEDULE_ARCHIVE_HTTP_'+archive.status)"),'current date must still reject unexpected archive errors');
assert.ok(scheduleLoader.indexOf("if(api?.status===404&&date>=fmt(jst()))")<scheduleLoader.indexOf("if(date<fmt(jst()))data=await historicalHeldVenues(date)"),'historical fallback ordering must be preserved');
console.log('PASS: historical schedule 404/503 fallback regression');

// Pages smoke must target each shortcut button itself, not a nested descendant.
const pagesPublishingWorkflow=fs.readFileSync('.github/workflows/deploy-pages.yml','utf8');
// The existing Pages site needs upload/deploy, not an extra settings API call.
// Keep the actual permission/environment gates; do not let a green static
// regression test claim the public URL is deployed.
assert.ok(!pagesPublishingWorkflow.includes('uses: actions/configure-pages@v5'),
  'Established Pages publish must not spend a settings-API call before upload');
assert.ok(pagesPublishingWorkflow.includes('uses: actions/upload-pages-artifact@v3')&&
          pagesPublishingWorkflow.includes('uses: actions/deploy-pages@v4')&&
          pagesPublishingWorkflow.includes('id-token: write')&&
          pagesPublishingWorkflow.includes('pages: write')&&
          pagesPublishingWorkflow.includes('name: github-pages'),
          'Pages artifact, deploy, environment and token safety gates must remain');
assert.ok(pagesPublishingWorkflow.includes("await page.locator('.race-detail-shortcuts button[data-race-view="),
  'Pages smoke must target the shortcut button directly');
assert.ok(!pagesPublishingWorkflow.includes("await shortcuts.locator("),
  'Pages smoke must never search for a nested button');

// Historical P0 browser coverage must span separate dates and venues with stored
// forecast, card, and result evidence; these are research-only, never formal scores.
const historicalPagesWorkflow=fs.readFileSync('.github/workflows/deploy-pages.yml','utf8');
for(const key of ['202610280101','202610310708','202611021905','202611031911']){
  assert.ok(historicalPagesWorkflow.split(key).length>=4,
    'Pages must inspect forecast, racecard and confirmed result for '+key);
}
assert.ok(historicalPagesWorkflow.includes("if(await page.locator('#resultComparison .comparison-hit, #resultComparison .comparison-miss').count())"),
  'P0 historical browser check must reject unverified scoring');

// A same-day race after its deadline must render as read-only and must not
// be relabeled as a verified predeadline forecast input.
assert.ok(historicalPagesWorkflow.includes("CLEAN_SAME_DAY_CUTOFF_READ_ONLY_BROWSER_PASS"),
  'Public browser must assert the Nov 3 completed-race read-only state');
assert.ok(historicalPagesWorkflow.includes("card?.source_audit?.race_card?.predeadline_verified!==false"),
  'Public browser must reject false predeadline evidence on closed racecards');

// Pages result verification must retry only transient delivery errors without
// treating a missing or mismatched historical result as proof.
assert.ok(historicalPagesWorkflow.includes("attempt<4;attempt++"),
  'Published-result HTTP 503 handling must have a bounded retry budget');
assert.ok(historicalPagesWorkflow.includes("[429,500,502,503,504].includes(archived.status())"),
  'Published-result delivery retries must be limited to transient HTTP errors');
assert.ok(historicalPagesWorkflow.includes("if(!archived.ok())throw Error('CLEAN published result unavailable:"),
  'Published-result checker must fail closed after retry exhaustion');

// GitHub Pages must ship the runtime navigation script referenced by index.html.
const pagesWorkflow=fs.readFileSync('.github/workflows/deploy-pages.yml','utf8');
assert.ok(html.includes("navScript.src='navigation.js'"),'site expects external navigation script');
assert.ok(pagesWorkflow.includes('cp index.html navigation.js candidates.html candidate_history.js public/'),'Pages must publish navigation and complete candidate history assets');
assert.ok(pagesWorkflow.includes('cmp -s public/navigation.js /tmp/clean-deployed-navigation.js'),'Pages must verify deployed navigation asset');
assert.ok(pagesWorkflow.includes('      - navigation.js'),'navigation changes must trigger Pages publication');
console.log('PASS: Pages navigation asset packaging and verification');

// Project-scoped GitHub Pages review links must not navigate to a missing /review route.
const navigation=fs.readFileSync('navigation.js','utf8');
assert.ok(navigation.includes("location.hostname.endsWith('.github.io')"),'restrict Pages route handling to GitHub Pages');
assert.ok(navigation.includes("target.searchParams.set('screen','review')"),'Pages review must navigate via single-page screen query');
assert.ok(navigation.includes("location.pathname.startsWith('/boat-edge-clean/')"),'Pages must restore review screen under project path');
console.log('PASS: Pages project-path review navigation regression');

// Forecast stays ticket-only; rates and conditional comparisons belong inside
// the race card, which has accessible basic/rates nested tabs.
const cardStart=html.indexOf('<section class="box" id="raceDataSection"');
const statsPane=html.indexOf('<section class="race-card-stats-pane"');
const forecastStart=html.indexOf('<section class="box" id="forecast"');
const resultFirst=html.indexOf('id="forecastResultFirstStatus"');
const prediction=html.indexOf('id="fourModeForecastRows"');
const leader=html.indexOf('id="forecastLeaderRows"');
const evidence=html.indexOf('id="forecastEvidenceStatus"');
assert.ok(cardStart>=0&&cardStart<statsPane&&statsPane<leader&&leader<evidence&&evidence<forecastStart&&forecastStart<resultFirst&&resultFirst<prediction,'card rates must be before forecast tickets in DOM');
const predictionPane=html.slice(forecastStart);
for(const forbidden of ['id="forecastLeaderRows"','class="forecast-statistics"','id="entryScenarioPanel"','id="legacyTopnResearch"'])
 assert.ok(!predictionPane.includes(forbidden),'forecast must show only prediction, not '+forbidden);
assert.ok(html.includes('id="raceCardCore"')&&html.includes('id="raceCardStatistics"'),'nested card tabs must exist');
assert.ok(html.includes('data-race-card-pane="rates"'),'rates subtab must be clickable');
assert.ok(navigation.includes("['出走表','card']")&&!navigation.includes("['連対率','stats']"),'four main race tabs only');
assert.ok(script.includes('function setRaceCardPane(pane)'),'rates tab selection must be functional');
for(let lane=1;lane<=6;lane++)assert.ok(html.includes('data-forecast-leader="'+lane+'"'),'missing leader '+lane);
assert.ok(script.includes('function selectForecastLeader(leader)'),'leader selection must respond to interaction');
assert.ok(script.includes('forecastEvidenceMirror.observe'),'verified predeadline preview must be mirrored without an extra fetch');
assert.ok(script.includes('forecastResultMirror.observe'),'validated confirmed result must be mirrored without an extra fetch');
assert.ok(html.includes('先頭艇として選択中')&&html.includes('未取得'),'missing stats must not be fabricated as 0%');
const historyPage=fs.readFileSync('selection.html','utf8');
assert.ok(historyPage.includes('id="savedPredictionHistory"')&&historyPage.includes('four_mode_forecasts/'),'saved pre-race tickets must remain inspectable after results');
assert.ok(historyPage.includes('history-10000.json')&&historyPage.includes('id="savedHistoryDate"'),'history should allow date selection and immutable result reconciliation');
assert.ok(historyPage.includes('3連単の的中率70%ではありません'),'70% winner-head research score must not be called a trifecta hit rate');
const historyScript=historyPage.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(historyScript,'saved history page must contain one inline script');
new vm.Script(historyScript,{filename:'selection.html'});
assert.ok(historyScript.includes('Date.parse(a.generated_at_jst)>=Date.parse(a.deadline_jst)'),'saved pre-race forecasts must predate cutoff');
assert.ok(historyScript.includes('a.race_code!==r.race_code'),'result and forecast must be same race');

console.log('PASS: four race tabs, card-level rates, and stored forecast/result history');

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
assert.ok(script.includes('loadForecastPriorResults();loadForecastPreview()}}else if(activeView'),'card-rate race changes must refresh prior results');

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

const archivedResultWorkflow=fs.readFileSync('.github/workflows/deploy-pages.yml','utf8');
assert.ok(archivedResultWorkflow.includes('CLEAN_RESULT_PUBLISHED_BROWSER_PASS'),'published browser test must verify a real archived race result');
assert.ok(archivedResultWorkflow.includes("#resultDetail .result-combo .boat-num"),'published browser test must inspect actual three boat numbers');

assert.ok(script.includes("async function fetchCleanResultArchive(code)"),'confirmed results require same-origin fallback');
assert.ok(script.includes("const local='confirmed_results/'+code+'.json'"),'local result archive path required');
assert.ok(script.includes("const sources=pages?[local,remote]:[remote,local]"),'Pages must prefer same-origin results while Render keeps Raw first');
assert.ok(script.includes("if(response.ok)return response"),'verified archive loader must fall back after unsuccessful responses');
assert.ok(script.includes("RESULT_RACE_CODE_INVALID"),'archive fallback must reject malformed race code');
const archivePublish=fs.readFileSync('.github/workflows/deploy-pages.yml','utf8');
assert.ok(archivePublish.includes('cp -R confirmed_results public/confirmed_results'),'Pages must publish confirmed archives used by fallback');

async function assertArchiveFetchOrder(host, statuses, expectedCalls, expectedStatus){
 const fn=script.match(/async function fetchCleanResultArchive\(code\)\{[\s\S]*?\n\}/)?.[0];
 assert.ok(fn,'production confirmed archive loader exists');
 const calls=[];
 const fakeFetch=async url=>{
  calls.push(url);
  return {status:statuses[calls.length-1],ok:statuses[calls.length-1]===200};
 };
 const ctx={location:{hostname:host},fetchTimed:fakeFetch,Response:class{constructor(body,{status}){this.status=status;this.ok=false}}};
 const fetchArchive=vm.runInNewContext(fn+';fetchCleanResultArchive',ctx);
 const response=await fetchArchive('202610310708');
 assert.equal(response.status,expectedStatus);
 assert.deepEqual(calls.map(url=>url.startsWith('confirmed_results/')?'local':'raw'),expectedCalls);
}
(async()=>{
 await assertArchiveFetchOrder('ikst2512-eng.github.io',[200],['local'],200);
 await assertArchiveFetchOrder('ikst2512-eng.github.io',[404,200],['local','raw'],200);
 await assertArchiveFetchOrder('boat-edge-clean.onrender.com',[200],['raw'],200);
 await assertArchiveFetchOrder('boat-edge-clean.onrender.com',[404,200],['raw','local'],200);
 await assertArchiveFetchOrder('ikst2512-eng.github.io',[404,404],['local','raw'],404);
})().catch(error=>{console.error(error);process.exitCode=1});

// Narrow iPhone four-mode ticket hierarchy regression.
const narrowTicketCss=html.match(/\/\* Narrow iPhone: readable picks outrank secondary odds without changing forecast data \*\/([\s\S]*?)<\/style>/)?.[1];
assert.ok(narrowTicketCss,'narrow iPhone ticket hierarchy must exist');
assert.match(narrowTicketCss,/@media\(max-width:420px\)/,'narrow mobile breakpoint');
assert.match(narrowTicketCss,/\.four-mode-forecast-grid\{grid-template-columns:minmax\(0,1fr\)/,'one forecast mode per row on narrow iPhones');
assert.match(narrowTicketCss,/\.four-mode-forecast-ticket \.four-mode-combo\{font-size:24px/,'ticket combination must be prominent');
assert.match(narrowTicketCss,/\.four-mode-forecast-ticket \.four-mode-odds\{font-size:11px/,'odds must remain secondary');

// Async race-switch regression: revalidate identity after every awaited parsing stage.
const fourModeSource=script.slice(script.indexOf('async function loadFourModeArchives('),script.indexOf('async function loadPredictions('));
assert.match(fourModeSource,/const data=await response\.json\(\);\s*if\(token!==window\.predictionRequestId\|\|sameRaceKey\(\)!==key\)return;/,'stale archived JSON must not paint a new race');
const cleanResultSource=script.slice(script.indexOf('async function loadResult(quiet=false)'),script.indexOf('async function loadResult(quiet=false)')+7000);
assert.match(cleanResultSource,/catch\(e\)\{if\(token===resultRequestId&&key===sameRaceKey\(\)\)payout\.textContent='3連単払戻金：未確認';\}\s*if\(token!==resultRequestId\|\|key!==sameRaceKey\(\)\)return;\s*comparison\.replaceChildren\(\);/,'stale payout must not replace another race comparison');

// Selected race cutoff must update once asynchronous schedule is verified.
assert.ok(script.includes('function syncActiveRaceDeadline()'),'selected cutoff sync helper exists');
assert.ok(script.includes('todayVenueRaces=data;renderDeadlines(data);updateRacePickerLabels();syncActiveRaceDeadline();'),'schedule resolution updates active race cutoff');
assert.ok(script.includes('syncActiveRaceDeadline();document.getElementById(\'previousRace\')'),'race selection updates active cutoff');

// HTTP 202 odds must retry only for the currently selected race and stop after a finite budget.
assert.match(script,/for\(let attempt=0;attempt<3;attempt\+\+\)/,'odds pending retries must be bounded');
assert.match(script,/if\(!enrichCurrent\(\)\)return;\s*res=await fetch\(oddsUrl/,'pending odds must abort for another race');
assert.match(script,/if\(res.status!==202\)break;/,'retry only pending HTTP 202');
assert.match(script,/if\(!enrichCurrent\(\)\)return;\s*if\(!res.ok\)/,'recheck race before applying completed odds');

// Confirmed full schedule excludes absent choices; partial/unpublished sources leave picker usable.
assert.ok(script.includes('function completeHeldSchedule()'),'full CLEAN schedule gate must be explicit');
assert.ok(script.includes('todayVenueRaces.partial_coverage!==true&&todayVenueRaces.historical_result_only!==true'),'partial or archive-derived schedule must not disable a real race');
assert.ok(script.includes('button.disabled=!hasConfirmedVenue(i+1)'),'confirmed absent venue must be visibly disabled');
assert.ok(script.includes('b.disabled=!hasConfirmedRace(s.venue+1,i)'),'confirmed absent race must be visibly disabled');
assert.ok(script.includes("if(!hasConfirmedVenue(i+1))return;venueTouched=true"),'confirmed venue guard on click');
assert.ok(script.includes("if(!hasConfirmedRace(s.venue+1,i))return;venueTouched=true"),'confirmed race guard on click');
assert.ok(script.includes("next>12||!hasConfirmedRace(s.venue+1,next)"),'previous/next navigation cannot bypass held-race gate');
assert.ok(script.includes("button.disabled=false;button.classList.remove('held')"),'failed or unpublished schedule must restore navigation');

// Racecard gate and visually disabled previous/next buttons must share the same complete-schedule predicate.
const raceDataGate=script.slice(script.indexOf('async function loadRaceData(force=false)'),script.indexOf('async function loadRaceData(force=false)')+1700);
assert.ok(raceDataGate.includes('if(completeHeldSchedule())'), 'partial/recovered schedule must not falsely hide archived six-boat racecards');
assert.ok(!raceDataGate.includes('todayVenueRaces.partial_coverage!==true'), 'racecard path must reuse the centralized complete-coverage gate');
assert.ok(script.includes("document.getElementById('previousRace').disabled=s.race===1||!hasConfirmedRace(s.venue+1,s.race-1)"), 'previous button must reflect confirmed absent race');
assert.ok(script.includes("document.getElementById('followingRace').disabled=s.race===12||!hasConfirmedRace(s.venue+1,s.race+1)"), 'next button must reflect confirmed absent race');

 // Live Pages browser test must report data states separately from four-tab navigation.
 assert.ok(archivePublish.includes('CLEAN_LIVE_DAY_TAB_STATUS'),'real-day published browser test must log tab status evidence');
 assert.ok(archivePublish.includes('tabEvidence[view].race!==selected.key'),'live tab data observation must retain race identity');
 assert.ok(archivePublish.includes("tabEvidence.result.confirmed="),'result tab must distinguish confirmed content from tab visibility');
 assert.ok(archivePublish.includes('not proof of complete sources'),'incomplete source evidence must remain explicitly qualified');

// Playwright Locator has no children() API; query direct descendants explicitly.
assert.ok(archivePublish.includes("page.locator('#predictionRows > *').count()"),'live status diagnostic must use supported locator selector');
assert.ok(!archivePublish.includes("page.locator('#predictionRows').children()"),'live status diagnostic must not call nonexistent children() API');

// Pre-race preview collector is implemented; unavailable or unverified values must not be labeled as "not implemented".
assert.ok(script.includes('対象レースの締切前6艇分の取得記録を検証できていません。'),'unverified exhibition copy must reflect evidence state');
assert.ok(!script.includes('直前データ収集が未実装'),'do not mislabel unverified source evidence as unimplemented collection');

// Real-day site diagnostics distinguish six visible placeholders from verified beforeinfo.
assert.ok(archivePublish.includes('tabEvidence.exhibit.sourceVerified='),'published exhibition diagnostic must include source verification flag');
assert.ok(archivePublish.includes("card?.verifiedPreview===true&&card?.source_audit?.beforeinfo?.status==='ok'"),'verification must require timestamp-gated snapshot and source audit');
assert.ok(archivePublish.includes('unverified_exhibition_mislabeled_verified'),'contradictory exhibition status must fail diagnostic');

// Candidate history: every Git-saved race on a selected date must survive cutoff.
assert.ok(html.includes('締切前3レースと開催場へ戻る'),'home shortcut stays visible');
assert.ok(script.includes('else if(!archive?.ok){'),'schedule fallback stays intact');
const candidateCode=fs.readFileSync('candidate_history.py','utf8');
const candidateController=fs.readFileSync('candidate_history.js','utf8');
const candidateStatic=fs.readFileSync('candidates.html','utf8');
const candidateTests=fs.readFileSync('test_candidate_history.py','utf8');
assert.ok(candidateHtml.includes('id="candidateCards"')&&candidateHtml.includes('src="/candidate_history.js"'),'Render candidate history must mount shared read-only renderer');
assert.ok(candidateHtml.includes('id="savedPredictionHistory"'),'new candidate list must preserve #1707 saved four-mode history');
assert.ok(!candidateHtml.includes('showTodayCandidates();'),'expired six-item live-only candidate scan must not run');
assert.ok(candidateStatic.includes('id="candidateCards"')&&candidateStatic.includes('src="candidate_history.js"'),'Pages static candidate history must mount shared renderer');
assert.ok(candidateCode.includes('daily_candidate_history')&&candidateCode.includes('confirmed_archive'),'candidate API must join independently saved results');
assert.ok(candidateController.includes("const onPages=location.pathname.endsWith('/candidates.html')"),'Pages candidate list must not need Render');
assert.ok(candidateController.includes("candidate_history/'+day+'.json"),'Pages must read day-scoped manifest');
assert.ok(candidateController.includes('result_status')&&candidateController.includes('confirmed_archive'),'results must be separately validated');
assert.ok(candidateTests.includes('test_shipped_november_eight_archive_is_not_capped'),'lossless archive count regression must exist');
const publishWorkflow=fs.readFileSync('.github/workflows/deploy-pages.yml','utf8');
assert.ok(publishWorkflow.includes('CLEAN_PAGES_CANDIDATE_NAV_VERIFIED'),'published browser must test candidate/review navigation');
assert.ok(publishWorkflow.includes('cp index.html navigation.js candidates.html candidate_history.js public/'),'Pages must publish candidate archive UI');
assert.ok(publishWorkflow.includes('public/candidate_history'),'Pages must publish day-scoped manifests');
assert.ok(publishWorkflow.includes('CLEAN_CANDIDATE_PUBLIC_DISPLAY'),'Pages must inspect real archived candidate list in browser');
assert.ok(publishWorkflow.includes("document.querySelectorAll('#candidateCards > details.candidate-history-card')"),'published browser must count every saved candidate card');
assert.ok(publishWorkflow.includes('candidate_archive_not_complete_'),'published count and uniqueness must be verified');
assert.ok(publishWorkflow.includes("candidateHref!=='/boat-edge-clean/candidates.html'"),'Pages candidate link must stay on Pages origin');
assert.ok(publishWorkflow.includes('CLEAN_CANDIDATE_PUBLIC_UNVERIFIED'),'evidence absence must not count as success');
console.log('PASS: exhaustive saved candidate history and independent result joins');

// Readability contract: BOATERS-like high-density comparison without turning
// action targets into tiny controls or re-separating independent original data.
const compactStyle=html.slice(html.indexOf('/* Compact race information density,'));
assert.ok(compactStyle.startsWith('/* Compact race information density,'),'compact design overrides must load after old styles');
for(const expected of [
 '.four-mode-forecast-grid .four-mode-forecast-ticket .four-mode-combo{font-size:15px}',
 '.four-mode-forecast-grid{grid-template-columns:repeat(2,minmax(0,1fr))',
 '.race-detail-shortcuts button{font-size:11px!important;min-height:42px',
 '#raceDataSection[data-view="exhibit"] .exhibition-values{',
 '#raceDataSection[data-view="exhibit"] .exhibition-original-values{',
 '#raceDataSection[data-view="exhibit"] .exhibition-boat{',
 'grid-template-columns:repeat(5,minmax(0,1fr))',
 'grid-template-columns:repeat(3,minmax(0,1fr))'
]){
 assert.ok(compactStyle.includes(expected),'compact six-boat layout missing '+expected);
}
assert.ok(script.includes("if(activeView==='exhibit')void loadOriginalExhibition(key,token,exhibitGrid,raw.meta.deadline);"),'compact rows must keep original feed per exact boat');
assert.ok(script.includes("['展示進入',courseLabel]"),'exhibition course must appear alongside each boat, not only as a global note');
assert.ok(script.includes("Number.isInteger(startCourse)&&startCourse>=1&&startCourse<=6?startCourse+'C':'—'"),'unverified or invalid exhibition course must not be synthesized');
assert.ok(!compactStyle.includes('display:none!important}\n#raceDataSection[data-view="exhibit"] .exhibition-boat'),'six-boat comparison must remain visible');
console.log('PASS: compact two-column forecasts, 6-boat exhibition rows and original measurements');

// Integrated exhibition: use the exact production CSV parser and async
// original-exhibition renderer against a deterministic DOM stub (no live data).
// This catches shifted-lane values, duplicate rows, incomplete source schemas,
// network absence and stale requests without changing forecast/scoring logic.
assert.ok(script.includes("metrics.dataset.originalExhibitionLane=String(lane)"),'each boat needs its own original exhibition host');
assert.ok(script.includes("if(activeView==='exhibit')void loadOriginalExhibition(key,token,exhibitGrid,raw.meta.deadline);"),'load original only after six boat cards and pass saved deadline');
assert.ok(!script.includes('originalExhibitionDetails'),'original exhibition cannot create a separate detached section');
assert.ok(html.includes('.exhibition-original-values'),'original measurements must share the six-boat card styling');
void (async()=>{
 const csvFn=script.split('\n').find(x=>x.startsWith('function csvFields('));
 const begin=script.indexOf("async function loadOriginalExhibition(key,token,grid,expectedDeadline=''){");
 const finish=script.indexOf("\nlet displayedRaceKey='';",begin);
 assert.ok(csvFn&&begin>=0&&finish>begin,'production original exhibition loader must be isolated');
 class FakeNode {
  constructor(tag='div'){this.tag=tag;this.children=[];this.textContent='';this.className='';this.isConnected=true;this.dataset={};}
  replaceChildren(...items){this.children=[...items]}
  append(...items){this.children.push(...items)}
 }
 const state={key:'20261104-01-11',token:1};
 const document={createElement:tag=>new FakeNode(tag)};
 const makeGrid=()=>{
  const status=new FakeNode('p'),holders=Array.from({length:6},()=>new FakeNode());
  status.textContent='読込中';
  return {status,holders,grid:{isConnected:true,
   querySelector(selector){
    if(selector==='#originalExhibitionStatus')return status;
    const match=selector.match(/^\[data-original-exhibition-lane="([1-6])"\]$/);
    return match?holders[Number(match[1])-1]:null;
   }}};
 };
 const head=['レースコード','計測数','計測項目1','計測項目2','締切時刻'];
 const data=['202611040111','2','1周','まわり足','20:03'];
 for(let lane=1;lane<=6;lane++)for(let k=1;k<=2;k++){
  head.push('艇'+lane+'_値'+k);
  data.push(String(lane*10+k));
 }
 const fixture=head.join(',')+'\n'+data.join(',')+'\n';
 let response={ok:true,status:200,text:async()=>fixture},blocked=false,finishRequest=null,fetchCalls=0;
 const win={get raceDataRequestId(){return state.token}};
 const load=vm.runInNewContext(csvFn+'\n'+script.slice(begin,finish)+'\nloadOriginalExhibition',{
   document,window:win,sameRaceKey:()=>state.key,activeView:'exhibit',
   fetchTimed:async()=>{fetchCalls++;return blocked?new Promise(resolve=>{finishRequest=resolve}):response},Error,Number,Set,Array,String
 });
 const ok=makeGrid();await load(state.key,state.token,ok.grid);
 assert.match(ok.status.textContent,/6艇分/);
 assert.equal(ok.status.dataset.originalState,'verified','success must expose source state');
 const shifted=makeGrid();await load(state.key,state.token,shifted.grid,'20:02');
 assert.equal(shifted.status.dataset.originalState,'deadline_mismatch','saved schedule and source cutoff differences must be visible');
 assert.match(shifted.status.textContent,/保存日程 20:02 \/ CSV 20:03/);
 assert.equal(shifted.holders[0].children.length,2,'a warning must not erase independently observed original values');
 // Real CSV archives include genuinely blank per-boat cells: preserve each
 // remaining lane and expose missingness without treating the whole row as complete.
 const sparseData=[...data];
 sparseData[head.indexOf('艇3_値1')]='';
 response={ok:true,status:200,text:async()=>head.join(',')+'\n'+sparseData.join(',')+'\n'};
 const sparse=makeGrid();await load(state.key,state.token,sparse.grid,'20:03');
 assert.equal(sparse.status.dataset.originalState,'partial_missing');
 assert.match(sparse.status.textContent,/一部欠測：1\/12項目/);
 assert.equal(sparse.holders[2].children[0].children[1].textContent,'—','missing source value must not be invented');
 assert.equal(sparse.holders[2].children[0].dataset.sourceValueState,'missing');
 assert.equal(sparse.holders[0].children[0].children[1].textContent,'11','other boats must stay intact');
 assert.equal(sparse.holders[0].children[0].dataset.sourceValueState,'present');
 const sparseDrift=makeGrid();await load(state.key,state.token,sparseDrift.grid,'20:02');
 assert.equal(sparseDrift.status.dataset.originalState,'partial_deadline_mismatch');
 assert.match(sparseDrift.status.textContent,/一部欠測/);
 assert.match(sparseDrift.status.textContent,/締切時刻不一致/);
 response={ok:true,status:200,text:async()=>fixture};

 ok.holders.forEach((holder,i)=>{
  assert.equal(holder.children.length,2,'must display two original source metrics for boat '+(i+1));
  assert.equal(holder.children[0].children[0].textContent,'1周');
  assert.equal(holder.children[0].children[1].textContent,String((i+1)*10+1),'no boat-to-boat shift');
  assert.equal(holder.children[1].children[0].textContent,'まわり足');
  assert.equal(holder.children[1].children[1].textContent,String((i+1)*10+2));
 });
 response={ok:false,status:404};
 const pending=makeGrid();await load(state.key,state.token,pending.grid);
 assert.match(pending.status.textContent,/未配信/);
 assert.equal(pending.status.dataset.originalState,'date_not_published');
 assert.ok(pending.holders.every(h=>h.children.length===1&&h.children[0].textContent==='オリ展：未公開'),'404 must not invent original values');
 const callsBeforeEdogawa=fetchCalls;
 state.key='20261104-03-11';
 const nonProvided=makeGrid();await load(state.key,state.token,nonProvided.grid);
 assert.match(nonProvided.status.textContent,/江戸川.*対象外/);
 assert.equal(fetchCalls,callsBeforeEdogawa,'non-providing venue must not trigger original feed request');
 assert.equal(nonProvided.status.dataset.originalState,'non_provided');
 assert.ok(nonProvided.holders.every(h=>h.children[0]?.textContent==='オリ展：非提供'),'Edogawa must be explicitly non-providing, not pending');
 state.key='20261104-01-11';
 response={ok:true,status:200,text:async()=>head.slice(0,-1).join(',')+'\n'+data.slice(0,-1).join(',')};
 const incomplete=makeGrid();await load(state.key,state.token,incomplete.grid);
 assert.match(incomplete.status.textContent,/検証できません/);
 assert.equal(incomplete.status.dataset.originalState,'invalid_source');
 assert.ok(incomplete.holders.every(h=>h.children[0].textContent==='オリ展：検証不可'),'missing lane column must reject whole source');
 response={ok:false,status:503};
 const offline=makeGrid();await load(state.key,state.token,offline.grid);
 assert.equal(offline.status.dataset.originalState,'transport_failed');
 assert.ok(offline.holders.every(h=>h.children[0].textContent==='オリ展：取得失敗'),'HTTP503 must not look like non-providing');
 response={ok:true,status:200,text:async()=>head.join(',')+'\n'+data.map((x,i)=>i===0?'202611040311':x).join(',')};
 const missing=makeGrid();await load(state.key,state.token,missing.grid);
 assert.equal(missing.status.dataset.originalState,'race_unlisted');
 assert.ok(missing.holders.every(h=>h.children[0].textContent==='オリ展：未収録'),'other race must not appear for selected race');
 blocked=true;
 const stale=makeGrid();const request=load(state.key,state.token,stale.grid);
 assert.equal(typeof finishRequest,'function','the stale request must be pending at the network boundary');
 state.token++;
 finishRequest({ok:true,status:200,text:async()=>fixture});
 await request;
 assert.equal(stale.status.textContent,'読込中','stale race request must not overwrite new race cards');
 assert.ok(stale.holders.every(h=>h.children.length===0),'stale request must not add measurements');
 console.log('PASS: original exhibition merged by exact boat number, independent data checks and stale-request protection');
})().catch(error=>{console.error('FAIL: per-boat exhibition integration',error);process.exitCode=1});


// Public review uses the Render-origin read-only holdout source on both Pages
// and Render. A cold-start HTTP 503 means "pending", never an empty cohort.
assert.ok(script.includes("const url='https://boat-edge-clean.onrender.com/api/signal70-holdout-status'"));
const holdoutStart=script.indexOf('let holdoutResearchRequest=0;');
const holdoutEnd=script.indexOf('async function loadTopNResearch(){',holdoutStart);
assert.ok(holdoutStart>=0&&holdoutEnd>holdoutStart,'production holdout review must be extractable');
void (async()=>{
 const source=script.slice(holdoutStart,holdoutEnd);
 const ready={
  schema:'CLEAN_SIGNAL70_HOLDOUT_STATUS_V1',independently_validated:false,
  later_holdout_days:12,archived_candidates:1486,evaluated_holdout_races:590,
  awaiting_result_races:23,audit_rejected_races:873
 };
 const exercise=async(responses,onTimeout)=>{
  const status={textContent:''};
  let count=0;
  const context={document:{getElementById:id=>id==='holdoutResearchStatus'?status:null},
   activeView:'review',fetchTimed:async url=>{
    assert.equal(url,'https://boat-edge-clean.onrender.com/api/signal70-holdout-status');
    const response=responses[Math.min(count++,responses.length-1)];
    return {status:response.code,ok:response.code===200,json:async()=>response.data};
   },setTimeout:callback=>{onTimeout?.(context);callback()}};
  const fn=vm.runInNewContext(source+'\nloadHoldoutResearch',context);
  await fn();
  return {status:status.textContent,count};
 };
 const pending={code:503,data:{error:'HOLDOUT_PENDING',running:true}};
 const ok={code:200,data:ready};
 const valid=await exercise([pending,ok]);
 assert.equal(valid.count,2);
 for(const expected of ['保存 1486件','参考評価 590件','結果待ち 23件','監査不合格 873件','未立証'])
  assert.ok(valid.status.includes(expected),'holdout public label '+expected);
 const neverReady=await exercise([pending]);
 assert.equal(neverReady.count,8,'research retry must be bounded');
 assert.match(neverReady.status,/処理待ち/,'pending must not become a fake 0% or HTTP error');
 const invalid=await exercise([{code:200,data:{...ready,audit_rejected_races:872}}]);
 assert.match(invalid.status,/取得・検証できません/,'invalid accounting cannot appear verified');
 const unavailable=await exercise([{code:503,data:{error:'HOLDOUT_UNAVAILABLE',running:false}}]);
 assert.equal(unavailable.count,1,'persistent backend fault must not trigger an unbounded spin');
 const canceled=await exercise([pending,ok],ctx=>{ctx.activeView='card'});
 assert.equal(canceled.count,1,'navigation away must suppress subsequent background fetches');
 console.log('PASS: public review holdout cold-start retry, origin, accounting and stale-view protection');
})().catch(error=>{console.error('FAIL: holdout review public regression',error);process.exitCode=1});
