/* All saved candidate races for the selected JST day. No post-race reconstruction. */
(()=>{
'use strict';
const status=document.getElementById('candidateStatus');
const root=document.getElementById('candidateCards');
const dayLabel=document.getElementById('todayCandidateDate');
const section=document.getElementById('todayCandidateRaces');
if(!status||!root||!dayLabel||!section)return;
const names=['桐生','戸田','江戸川','平和島','多摩川','浜名湖','蒲郡','常滑','津','三国','びわこ','住之江','尼崎','鳴門','丸亀','児島','宮島','徳山','下関','若松','芦屋','福岡','唐津','大村'];
const pad=n=>String(n).padStart(2,'0');
const onPages=location.pathname.endsWith('/candidates.html')||location.hostname.endsWith('.github.io');
const today=()=>{
 const p=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
 return p.year+'-'+p.month+'-'+p.day;
};
const validDay=x=>typeof x==='string'&&/^20\d{2}-\d{2}-\d{2}$/.test(x)&&!Number.isNaN(Date.parse(x+'T12:00:00+09:00'));
let selectedDay=validDay(new URLSearchParams(location.search).get('date'))?new URLSearchParams(location.search).get('date'):today();
let requestId=0;
let activeFilter="pass";
let savedRaces=[];
let selectionAvailable=false;
document.getElementById('todayCandidateHeading').textContent='候補レース｜研究条件クリア（暫定）';
const toolbar=document.createElement('div');toolbar.className='candidate-history-toolbar';
const label=document.createElement('label');label.textContent='表示日（日本時間） ';
const dateInput=document.createElement('input');dateInput.type='date';dateInput.id='candidateHistoryDate';dateInput.value=selectedDay;dateInput.max=today();label.append(dateInput);
const todayButton=document.createElement('button');todayButton.type='button';todayButton.textContent='今日の候補';
toolbar.append(label,todayButton);
dayLabel.replaceChildren(toolbar);
const filters=document.createElement('div');filters.id='candidateHistoryFilters';filters.setAttribute('role','group');filters.setAttribute('aria-label','候補レースの研究フィルター');
section.insertBefore(filters,root);
const css=document.createElement('style');
css.textContent='.candidate-history-toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.candidate-history-toolbar label{font-size:13px;font-weight:800}.candidate-history-toolbar input{font-size:16px;padding:9px;border:1px solid #b4c9de;border-radius:7px}.candidate-history-toolbar button{padding:10px 13px;border:1px solid #93b5d2;border-radius:8px;background:#ecf5ff;color:#164a80;font-weight:800;cursor:pointer}#candidateCards{display:grid;grid-template-columns:1fr;gap:8px}.candidate-history-card{min-width:0;overflow-wrap:anywhere}.candidate-history-card summary{cursor:pointer;font-weight:800;line-height:1.6;padding:4px 0}.candidate-history-card summary:focus-visible{outline:3px solid #1369b3}.candidate-history-card .candidate-detail{padding-top:9px;border-top:1px solid #e1e9f1}.candidate-history-card .candidate-tickets{line-height:1.8;font-size:14px;overflow-wrap:anywhere}.candidate-history-card .candidate-finish{font-size:15px;font-weight:900;color:#114b80}.candidate-history-card .candidate-links{display:flex;flex-wrap:wrap;gap:12px;margin:10px 0}.candidate-history-card .candidate-links a{font-weight:800}.candidate-mode{border-top:1px solid #e0e8ef;padding:8px 0}.candidate-mode strong{display:block;margin-bottom:4px}#candidateHistoryFilters{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}#candidateHistoryFilters button{cursor:pointer}#candidateHistoryFilters button[aria-pressed="true"]{background:#174a77;color:white;border-color:#174a77}.candidate-empty{padding:16px;background:#f8fbff;border-radius:8px}.candidate-signal{font-weight:700;color:#174a77}';
document.head.append(css);
function text(tag,value,klass){
 const el=document.createElement(tag);el.textContent=value;if(klass)el.className=klass;return el;
}
function localRaceLink(race,screen){
 const url=onPages?new URL('./',location.href):new URL('/forecast',location.origin);
 url.searchParams.set('date',selectedDay);
 url.searchParams.set('venue',String(race.venue));
 url.searchParams.set('race',String(race.race));
 url.searchParams.set('screen',screen);
 return url.pathname+url.search;
}
async function loadFourModes(code,target){
 const url=onPages?'https://raw.githubusercontent.com/ikst2512-eng/boat-edge-clean/main/four_mode_forecasts/'+code+'.json':
  '/api/four-mode-archive?code='+encodeURIComponent(code);
 try{
  const response=await fetch(url,{cache:'no-store',signal:AbortSignal.timeout(14000)});
  if(response.status===404){target.textContent='4モードの保存予想はありません。';return;}
  if(!response.ok)throw Error('HTTP '+response.status);
  const d=await response.json();
  if(onPages){
   // Git-stored source record, not Render's reduced research API wrapper.
   if(d.schema!=='CLEAN_FOUR_MODES_PREDEADLINE_V1'||d.race_code!==code||
      typeof d.generated_at_jst!=='string'||typeof d.deadline_jst!=='string'||
      !d.generated_at_jst.endsWith('+09:00')||!d.deadline_jst.endsWith('+09:00')||
      !(Date.parse(d.generated_at_jst)<Date.parse(d.deadline_jst))||!d.modes)throw Error('保存予想の検証待ち');
   for(const id of ['hit','balance','narrow','hole']){
    if(!Array.isArray(d.modes[id]?.tickets))throw Error('4モード原本不一致');
    d.modes[id].label={hit:'本命',balance:'バランス',narrow:'絞り',hole:'穴'}[id];
   }
  }else if(d.status!=='historical_research_only'||d.race_code!==code||
      d.production_forecast!==false||d.verified_first_git_add!==false||!d.modes){
   throw Error('保存予想の検証待ち');
  }
  target.replaceChildren(text('p','4モードの保存済み研究予想（初回Git登録未検証・正式認定ではありません）','notes'));
  for(const id of ['hit','balance','narrow','hole']){
   const m=d.modes[id],list=m?.tickets;
   if(!Array.isArray(list)||!list.length||list.some(x=>typeof x.combo!=='string'||typeof x.p!=='number'))continue;
   const group=document.createElement('div');group.className='candidate-mode';
   group.append(text('strong',(m.label||id)+'｜'+list.length+'点'));
   group.append(text('div',list.map(x=>x.combo).join(' ／ '),'candidate-tickets'));
   target.append(group);
  }
 }catch(err){target.textContent='4モードを確認できません。通信または保存原本の検証待ちです。';}
}
function showRace(race){
 const node=document.createElement('details');node.className='card candidate-history-card';node.dataset.raceCode=race.race_code;
 const name=(names[race.venue-1]||pad(race.venue))+' '+race.race+'R';
 const deadline=typeof race.deadline_jst==='string'?race.deadline_jst.slice(11,16):'未確認';
 const confirmed=race.result_status==='confirmed_archive'&&/^[1-6]-[1-6]-[1-6]$/.test(race.finish||'');
 const resultText=confirmed?'確定 '+race.finish:race.result_status==='unverified'?'結果原本の検証待ち':'結果未保存';
 const verifiedPayout=confirmed&&race.payout_status==='verified_independent'&&Number.isInteger(race.payout_yen_per_100)&&race.payout_yen_per_100>=100;
 const category={
  research_70_pass:'研究条件クリア（参考）',
  research_70_below:'研究基準未達',
  unassessed:'選定不能'
 }[race.selection_status]||'選定不能';
 const summary=text('summary',category+'｜'+name+'｜締切 '+deadline+'｜'+resultText);
 node.append(summary);
 const detail=document.createElement('div');detail.className='candidate-detail';
 const saved=race.forecast_status==='saved_research_unattested'&&Array.isArray(race.tickets)&&race.tickets.length;
 if(race.selection_status==='research_70_pass'||race.selection_status==='research_70_below'){
  detail.append(text('p','1着候補上位2艇のモデル確率合計 '+race.head_top2_model_pct.toFixed(2)+'%｜研究用・3連単的中率ではありません。','candidate-signal'));
 }else detail.append(text('p','研究基準の判定に必要な保存済み入力が不足・未検証です。','notes'));
 detail.append(text('p',saved?'締切前に保存された研究予想 '+race.tickets.length+'点（正式認定前）':'候補として保存された記録あり。買い目原本の検証待ち。','notes'));
 if(saved){
  detail.append(text('div',race.tickets.join(' ／ '),'candidate-tickets'));
  if(confirmed){
   const rank=race.tickets.indexOf(race.finish);
   detail.append(text('p',rank>=0?'確定 '+race.finish+'｜保存済み研究予想の'+(rank+1)+'番目と一致（参考照合）':'確定 '+race.finish+'｜保存済み研究予想には該当なし（参考照合）','candidate-finish'));
  }
 }
 if(confirmed){
  detail.append(text('p',verifiedPayout?'3連単払戻：'+race.payout_yen_per_100.toLocaleString('ja-JP')+'円（100円あたり・独立保存原本照合済み）':'3連単払戻：未確認（推定値は表示しません）',verifiedPayout?'candidate-finish':'notes'));
 }else detail.append(text('p',race.result_status==='unverified'?'結果ファイルが未検証のため判定保留。':'確定結果の保存・反映待ち。後から予想を生成しません。','notes'));

 detail.append(text('p','この一覧は保存済み原本の参照です。Git初回登録・正式T−12認定・実際の的中率は証明していません。','notes'));
 const links=document.createElement('nav');links.className='candidate-links';
 for(const [label,screen] of [['予想画面へ','forecast'],['結果画面へ','result']]){
  const a=document.createElement('a');a.href=localRaceLink(race,screen);a.textContent=label;links.append(a);
 }
 detail.append(links);
 const modes=document.createElement('div');modes.className='candidate-modes';modes.append(text('p','詳細を開くと保存済み4モードを確認します。','notes'));detail.append(modes);
 let loaded=false;
 node.addEventListener('toggle',()=>{if(!node.open||loaded)return;loaded=true;loadFourModes(race.race_code,modes);});
 node.append(detail);return node;
}
function renderSavedRaces(d){
 const pass=savedRaces.filter(r=>r.selection_status==='research_70_pass');
 const below=savedRaces.filter(r=>r.selection_status==='research_70_below');
 const unknown=savedRaces.filter(r=>r.selection_status==='unassessed');
 const categories=[
  ['pass','研究条件クリア',pass.length],['below','基準未達',below.length],
  ['unassessed','判定不能',unknown.length],['all','全保存履歴',savedRaces.length]
 ];
 filters.replaceChildren();
 for(const [key,name,count] of categories){
  const button=document.createElement('button');button.type='button';button.dataset.candidateFilter=key;
  button.textContent=name+' '+count+'件';button.setAttribute('aria-pressed',String(activeFilter===key));
  button.addEventListener('click',()=>{activeFilter=key;renderSavedRaces(d);});
  filters.append(button);
 }
 let visible=activeFilter==='pass'?pass:activeFilter==='below'?below:activeFilter==='unassessed'?unknown:savedRaces;
 if(activeFilter==='pass')visible=[...visible].sort((a,b)=>(b.head_top2_model_pct??-1)-(a.head_top2_model_pct??-1)||a.race_code.localeCompare(b.race_code));
 const fragment=document.createDocumentFragment();
 for(const race of visible)fragment.append(showRace(race));
 if(!visible.length)fragment.append(text('p',activeFilter==='pass'?'この日に研究条件を満たした保存済みレースはありません。全保存履歴も確認できます。':'この区分に保存済みレースはありません。','notes candidate-empty'));
 root.replaceChildren(fragment);
 status.textContent='保存候補 '+d.candidate_count+'件｜研究条件クリア '+pass.length+'件｜基準未達 '+below.length+'件｜判定不能 '+unknown.length+'件｜表示 '+visible.length+'件｜研究予想あり '+d.research_forecast_count+'件｜確定結果あり '+d.confirmed_result_count+'件｜払戻照合済み '+(Number.isInteger(d.payout_verified_count)?d.payout_verified_count:'未集計')+'件'+(selectionAvailable?'（保存原本からの未検証研究判定）':'（選定情報は未配信・全履歴を表示）');
}
async function loadDay(){
 const token=++requestId;
 root.replaceChildren();filters.replaceChildren();status.textContent=selectedDay+'の候補原本を確認中…';
 const day=selectedDay.replaceAll('-','');
 try{
  const endpoint=onPages?'candidate_history/'+day+'.json':'/api/candidate-history?date='+day;
  const response=await fetch(endpoint,{cache:'no-store',signal:AbortSignal.timeout(20000)});
  if(onPages&&response.status===404){status.textContent='この日付の候補履歴はまだ公開されていません。候補0件とは断定しません。';return;}
  if(!response.ok)throw Error('HTTP '+response.status);
  const d=await response.json();
  if(token!==requestId)return;
  if(d.ok!==true||d.schema!=='CLEAN_CANDIDATE_HISTORY_V1'||d.date!==day||
     !Array.isArray(d.races)||d.candidate_count!==d.races.length||d.production_forecast!==false)throw Error('保存原本の応答形式を検証できません');
  const seen=new Set();
  for(const row of d.races){
   if(!/^20\d{10}$/.test(row.race_code||'')||!row.race_code.startsWith(day)||seen.has(row.race_code)||!Number.isInteger(row.venue)||row.venue<1||row.venue>24||!Number.isInteger(row.race)||row.race<1||row.race>12)throw Error('候補レースの一意性を検証できません');
   if(row.payout_status==='verified_independent'){
    if(row.result_status!=='confirmed_archive'||!Number.isInteger(row.payout_yen_per_100)||row.payout_yen_per_100<100)throw Error('保存払戻の証拠が不一致');
   }else if(row.payout_yen_per_100!==null&&row.payout_yen_per_100!==undefined)throw Error('未検証払戻値を拒否しました');
   seen.add(row.race_code);
  }
  if(Number.isInteger(d.payout_verified_count)&&d.payout_verified_count!==d.races.filter(x=>x.payout_status==='verified_independent').length)throw Error('払戻原本の件数が不一致');
  selectionAvailable=d.selection_rule==='top2_head_mass_ge_70_research_only_v1';
  if(d.selection_rule!==undefined&&!selectionAvailable)throw Error('未知の研究選定ルール');
  if(selectionAvailable){
   const counts={research_70_pass:0,research_70_below:0,unassessed:0};
   for(const race of d.races){
    if(!Object.hasOwn(counts,race.selection_status))throw Error('不正な研究選定分類');
    counts[race.selection_status]++;
    const mass=race.head_top2_model_pct;
    if(race.selection_status==='unassessed' ? mass!==null :
       !(typeof mass==='number'&&Number.isFinite(mass)&&mass>=0&&mass<=100))
       throw Error('不正な研究選定値');
   }
   if(counts.research_70_pass!==d.research_70_pass_count||
      counts.research_70_below!==d.research_70_below_count||
      counts.unassessed!==d.research_unassessed_count)throw Error('研究分類の件数不一致');
  }else for(const race of d.races){race.selection_status='unassessed';race.head_top2_model_pct=null;}
  savedRaces=d.races;
  activeFilter=selectionAvailable?'pass':'all';
  renderSavedRaces(d);
 }catch(err){
  if(token!==requestId)return;
  status.textContent='候補履歴を読み込めません（'+String(err?.message||'通信エラー').slice(0,80)+'）。通信障害を候補0件と扱いません。';
 }
}
function selectDay(next,push=true){
 if(!validDay(next)||next>today())return;
 selectedDay=next;dateInput.value=next;
 if(push){const url=new URL(location.href);url.searchParams.set('date',next);history.pushState(null,'',url);}
 loadDay();
}
dateInput.addEventListener('change',()=>selectDay(dateInput.value));
todayButton.addEventListener('click',()=>selectDay(today()));
window.addEventListener('popstate',()=>{const q=new URLSearchParams(location.search).get('date');selectDay(validDay(q)?q:today(),false);});
loadDay();
})();
