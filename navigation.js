(()=>{'use strict';
const nav=document.querySelector('.site-global-nav');
if(!nav)return;
const params=location.search;
nav.innerHTML='<a href="/review">検証</a><a href="/selection">購入候補</a>';
nav.setAttribute('aria-label','検証と購入候補');
nav.classList.add('compact-nav');
nav.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>{
 const destination=new URL(link.href);
 const date=s?.date,venue=s?.venue,race=s?.race;
 if(/^\d{4}-\d{2}-\d{2}$/.test(date||'')&&Number.isInteger(venue)&&venue>=0&&venue<24&&Number.isInteger(race)&&race>=1&&race<=12){
  destination.searchParams.set('date',date);
  destination.searchParams.set('venue',String(venue+1));
  destination.searchParams.set('race',String(race));
 }
 link.href=destination.pathname+destination.search;
}));
const logo=document.querySelector('.site-head .logo');
if(logo){const a=document.createElement('a');a.href='/';a.className=logo.className+' logo-link';a.textContent=logo.textContent;a.setAttribute('aria-label','開催場を選ぶ画面に戻る');logo.replaceWith(a);}
const strip=document.querySelector('.active-race-strip');
if(strip){const a=document.createElement('a');a.href='/';a.className='back-to-venues';a.textContent='‹ 場を選び直す';strip.prepend(a);
const update=()=>{const home=document.querySelector('[data-home-only]');a.hidden=!!home&&!home.hidden;};
update();
new MutationObserver(update).observe(document.querySelector('[data-home-only]'),{attributes:true,attributeFilter:['hidden']});}
const css=document.createElement('style');
css.textContent='.logo-link{color:inherit;text-decoration:none}.logo-link:focus-visible,.back-to-venues:focus-visible{outline:3px solid #7ab8ff;outline-offset:2px}.site-global-nav.compact-nav{display:flex;justify-content:flex-end;gap:10px;padding:8px 16px;overflow:visible}.site-global-nav.compact-nav a{flex:0 0 auto;white-space:nowrap;padding:10px 16px;border:1px solid #cbd9e8;border-radius:9px;text-decoration:none;font-weight:800}.back-to-venues{display:inline-flex;align-items:center;color:#155eae;text-decoration:none;font-weight:800;border:1px solid #cbd9e8;border-radius:9px;padding:7px 10px;background:white}.back-to-venues[hidden]{display:none!important}@media(max-width:420px){.site-global-nav.compact-nav{justify-content:center}.site-global-nav.compact-nav a{flex:1;text-align:center}}';
document.head.append(css);

// Navigation history for in-page race/detail changes. Browser back/forward restore both
// selected race and active panel without resetting to the home screen.
const toolbar=document.createElement('div');toolbar.className='race-browser-toolbar';
const back=document.createElement('button');back.type='button';back.textContent='‹ 戻る';back.setAttribute('aria-label','ひとつ前の画面に戻る');
const home=document.createElement('a');home.href='/';home.textContent='開催場を選ぶ';home.setAttribute('aria-label','開催場選択へ戻る');
toolbar.append(back,home);
const navHost=document.querySelector('.site-global-nav');navHost?.insertAdjacentElement('afterend',toolbar);
const originalSetView=typeof setView==='function'?setView:null;
const originalRender=typeof render==='function'?render:null;
let restoring=false;
let syncScheduled=false;
const scheduleSync=()=>{if(syncScheduled||restoring)return;syncScheduled=true;queueMicrotask(()=>{syncScheduled=false;sync();});};
const snapshot=()=>({date:s.date,venue:s.venue,race:s.race,view:activeView});
const key=p=>[p.date,p.venue,p.race,p.view].join('|');
const requestedScreen=new URL(location.href).searchParams.get('screen');
if(location.pathname==='/'&&['forecast','card','exhibit','result','review'].includes(requestedScreen)&&originalSetView&&originalRender){
 originalSetView(requestedScreen);
 originalRender();
}
const initial=snapshot();
const existing=history.state&&history.state.boatEdgeNav?history.state:null;
let position=existing?existing.position:0;
let current=existing?existing.snapshot:initial;
history.replaceState({boatEdgeNav:true,position,snapshot:current},'',location.href);
const sync=()=>{
 if(restoring)return;
 const next=snapshot();if(key(next)===key(current))return;
 position+=1;current=next;
 const u=new URL(location.href);
 u.searchParams.set('date',next.date);
 u.searchParams.set('venue',String(next.venue+1));
 u.searchParams.set('race',String(next.race));
 u.searchParams.set('screen',next.view);
 history.pushState({boatEdgeNav:true,position,snapshot:next},'',u);
 refresh();
};
const refresh=()=>{back.disabled=false;back.setAttribute('aria-disabled','false');};
if(originalSetView){
 setView=function(view){const url=location.href,state=history.state;const result=originalSetView(view);history.replaceState(state,'',url);scheduleSync();return result;};
}
if(originalRender){
 render=function(){const url=location.href,state=history.state;const result=originalRender();history.replaceState(state,'',url);scheduleSync();return result;};
}
window.addEventListener('popstate',event=>{
 const state=event.state;
 if(!state?.boatEdgeNav||!state.snapshot)return;
 restoring=true;
 position=state.position;current=state.snapshot;
 const v=current;
 s.date=v.date;s.venue=v.venue;s.race=v.race;
 if(originalSetView)originalSetView(v.view);
 if(originalRender)originalRender();
 history.replaceState(state,'',location.href);
 restoring=false;refresh();
});
back.addEventListener('click',()=>{if(position>0||document.referrer&&new URL(document.referrer).origin===location.origin)history.back();else location.assign('/');});
refresh();
const browserStyle=document.createElement('style');
browserStyle.textContent='.race-browser-toolbar{display:flex;justify-content:space-between;gap:8px;max-width:900px;margin:0 auto;padding:8px 14px}.race-browser-toolbar button,.race-browser-toolbar a{font-size:14px;font-weight:800;border:1px solid #cbd9e8;border-radius:9px;background:#fff;color:#174066;padding:9px 14px;text-decoration:none;min-height:40px}.race-browser-toolbar button:disabled{opacity:.5}.race-browser-toolbar a{text-align:center}@media(max-width:420px){.race-browser-toolbar button,.race-browser-toolbar a{flex:1}}';
document.head.append(browserStyle);

const details=document.createElement('nav');details.className='race-detail-shortcuts';
details.setAttribute('aria-label','選択レースの情報');
for(const [label,view] of [['予想','forecast'],['出走表','card'],['展示・直前','exhibit'],['結果','result']]){
 const b=document.createElement('button');b.type='button';b.textContent=label;b.dataset.raceView=view;
 b.addEventListener('click',()=>{if(typeof setView!=='function'||typeof render!=='function')return;setView(view);render();document.querySelector(view==='forecast'?'#forecast':view==='result'?'#resultSection':'#raceDataSection')?.scrollIntoView({block:'start'});});
 details.append(b);
}
toolbar.insertAdjacentElement('afterend',details);
const updateDetails=()=>{
 const isHome=!!document.querySelector('[data-home-only]:not([hidden])');
 details.hidden=isHome;details.querySelectorAll('button').forEach(b=>{b.setAttribute('aria-current',String(b.dataset.raceView===activeView));});
};
updateDetails();
const raceHome=document.querySelector('[data-home-only]');
if(raceHome)new MutationObserver(updateDetails).observe(raceHome,{attributes:true,attributeFilter:['hidden']});
window.addEventListener('popstate',()=>queueMicrotask(updateDetails));
details.addEventListener('click',()=>queueMicrotask(updateDetails));
const compactRaceCards=container=>{
 if(!container)return;
 const clean=()=>{
  for(const actions of container.querySelectorAll('.clean-race-actions')){
   if(actions.dataset.compact==='1')continue;
   const buttons=[...actions.querySelectorAll('button')];
   const prediction=buttons.find(b=>b.textContent.trim()==='AI予想');
   if(!prediction)continue;
   prediction.textContent='このレースの予想を見る';
   for(const b of buttons)if(b!==prediction)b.remove();
   actions.dataset.compact='1';
  }
 };
 new MutationObserver(clean).observe(container,{childList:true,subtree:true});
 clean();
};
compactRaceCards(document.getElementById('homeRaceCardList'));
compactRaceCards(document.getElementById('resultList'));
const detailStyles=document.createElement('style');
detailStyles.textContent='.race-detail-shortcuts{display:flex;gap:5px;max-width:900px;margin:0 auto;padding:0 14px 9px}.race-detail-shortcuts[hidden]{display:none!important}.race-detail-shortcuts button{min-width:0;flex:1;font-size:12px;padding:10px 3px;border:1px solid #cbd9e8;background:white;border-radius:8px;color:#174066;font-weight:800}.race-detail-shortcuts button[aria-current="true"]{background:#155eae;border-color:#155eae;color:white}.clean-race-actions{display:flex}.clean-race-actions button{width:100%;max-width:320px;background:#e9f3ff;color:#14528d;font-weight:800}';
document.head.append(detailStyles);
})();