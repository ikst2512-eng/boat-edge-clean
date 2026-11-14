(()=>{'use strict';
if(document.documentElement.dataset.cleanNavigationInit==='1')return;
const nav=document.querySelector('.site-global-nav');
if(!nav){
  // Render-only standalone report screens reuse navigation.js and retain their back link.
  // Do not initialize the race-history state machine on standalone screens.
  if(document.documentElement.dataset.cleanStandaloneNavigationInit==='1'||document.querySelector('.race-browser-toolbar'))return;
  document.documentElement.dataset.cleanStandaloneNavigationInit='1';
  if(document.querySelector('.race-browser-toolbar'))return;
  const bar=document.createElement('nav');
  bar.setAttribute('aria-label','ページ移動');
  bar.className='secondary-page-navigation';
  const back=document.createElement('button');back.type='button';back.textContent='‹ 前のページに戻る';
  const fallback=document.createElement('a');fallback.textContent='レース選択へ';
  const params=new URLSearchParams(location.search);
  const url=new URL('/',location.origin);
  for(const field of ['date','venue','race'])if(params.has(field))url.searchParams.set(field,params.get(field));
  fallback.href=url.pathname+url.search;
  back.addEventListener('click',()=>{
   if(document.referrer){try{if(new URL(document.referrer).origin===location.origin){history.back();return;}}catch(_){}}
   location.assign(fallback.href);
  });
  bar.append(back,fallback);
  const header=document.querySelector('header');
  if(header)header.insertAdjacentElement('afterend',bar);else document.body.prepend(bar);
  const style=document.createElement('style');
  style.textContent='.secondary-page-navigation{display:flex;gap:8px;max-width:900px;margin:8px auto;padding:0 12px}.secondary-page-navigation button,.secondary-page-navigation a{min-height:44px;flex:1;display:flex;justify-content:center;align-items:center;border:1px solid #bed0e1;border-radius:9px;background:#fff;color:#174066;font-size:14px;font-weight:800;text-decoration:none;padding:8px;cursor:pointer}';
  document.head.append(style);
  return;
}
document.documentElement.dataset.cleanNavigationInit='1';
// GitHub Pages project sites cannot serve Render's /review route directly.
// Use the existing single-page screen query without changing Render routes.
if(location.hostname.endsWith('.github.io')&&location.pathname.startsWith('/boat-edge-clean/')){
 const review=nav.querySelector('a[href="/review"]');
 if(review){const target=new URL(location.href);target.searchParams.set('screen','review');review.href=target.pathname+target.search;}
 // Candidate history is a static GitHub Pages document, not a sleeping Render redirect.
 const selection=document.querySelector('.site-head .header-candidate-tab[href="/selection"]');
 if(selection)selection.href='/boat-edge-clean/candidates.html';
}
document.querySelectorAll('.site-global-nav a, .site-head .header-candidate-tab').forEach(link=>link.addEventListener('click',()=>{
 const destination=new URL(link.href);
 const state=typeof s==='undefined'?null:s;
 const date=state?.date,venue=state?.venue,race=state?.race;
 if(/^\d{4}-\d{2}-\d{2}$/.test(date||'')&&Number.isInteger(venue)&&venue>=0&&venue<24&&Number.isInteger(race)&&race>=1&&race<=12){
  destination.searchParams.set('date',date);
  destination.searchParams.set('venue',String(venue+1));
  destination.searchParams.set('race',String(race));
 }
 link.href=destination.origin===location.origin?destination.pathname+destination.search:destination.href;
}));
const logo=document.querySelector('.site-head .logo');
if(logo){const a=document.createElement('a');a.href=location.hostname.endsWith('.github.io')&&location.pathname.startsWith('/boat-edge-clean/')?'/boat-edge-clean/':'/';a.className=logo.className+' logo-link';a.textContent=logo.textContent;a.setAttribute('aria-label','開催場を選ぶ画面に戻る');logo.replaceWith(a);}
const css=document.createElement('style');
css.textContent='.logo-link{color:inherit;text-decoration:none}.logo-link:focus-visible{outline:3px solid #7ab8ff;outline-offset:2px}.site-global-nav.compact-nav{display:flex;justify-content:flex-end;gap:10px;padding:8px 16px;overflow:visible}.site-global-nav.compact-nav a{flex:0 0 auto;white-space:nowrap;padding:10px 16px;border:1px solid #cbd9e8;border-radius:9px;text-decoration:none;font-weight:800}@media(max-width:420px){.site-global-nav.compact-nav{justify-content:center}.site-global-nav.compact-nav a{flex:1;text-align:center}}';
document.head.append(css);

// Standalone navigation pages may not bootstrap race state; keep global links usable.
if(typeof s==='undefined'||typeof activeView==='undefined')return;

// Navigation history for in-page race/detail changes. Browser back/forward restore both
// selected race and active panel without resetting to the home screen.
const back=document.getElementById('raceViewBack');
const originalSetView=typeof setView==='function'?setView:null;
const originalRender=typeof render==='function'?render:null;
// Preserve the WebKit history ownership guard merged in #1706.
if(originalSetView&&originalRender)window.__boatEdgeNavigationOwnsHistory=true;
let restoring=false;
let syncScheduled=false;
const scheduleSync=()=>{if(syncScheduled||restoring)return;syncScheduled=true;queueMicrotask(()=>{syncScheduled=false;sync();});};
const focusedPane=()=>activeView==='card'&&typeof raceCardPane!=='undefined'?raceCardPane:null;
const snapshot=()=>({date:s.date,venue:s.venue,race:s.race,view:activeView,pane:activeView==='card'?focusedPane():null});
const key=p=>[p.date,p.venue,p.race,p.view,p.pane||''].join('|');
const requestedScreen=new URL(location.href).searchParams.get('screen');
if((location.pathname==='/'||location.pathname.startsWith('/boat-edge-clean/'))&&['forecast','card','exhibit','result','review'].includes(requestedScreen)&&originalSetView&&originalRender){
 originalSetView(requestedScreen);
 if(requestedScreen==='card'&&new URL(location.href).searchParams.get('pane')==='rates'&&typeof setRaceCardPane==='function')setRaceCardPane('rates');
 originalRender();
}
const initial=snapshot();
const existing=history.state&&history.state.boatEdgeNav?history.state:null;
let position=existing?existing.position:0;
let current=existing?existing.snapshot:initial;
if(!existing)history.replaceState({boatEdgeNav:true,position,snapshot:current},'',location.href);
const sync=()=>{
 if(restoring)return;
 const next=snapshot();if(key(next)===key(current))return;
 position+=1;current=next;
 const u=new URL(location.href);
 u.searchParams.set('date',next.date);
 u.searchParams.set('venue',String(next.venue+1));
 u.searchParams.set('race',String(next.race));
 u.searchParams.set('screen',next.view);
 if(next.view==='card'&&next.pane==='rates')u.searchParams.set('pane','rates');else u.searchParams.delete('pane');
 history.pushState({boatEdgeNav:true,position,snapshot:next},'',u);

};
const restoreNavigationLocation=(url,state)=>{
 const after=history.state;
 if(location.href!==url||(after!==state&&JSON.stringify(after)!==JSON.stringify(state)))
  history.replaceState(state,'',url);
};
if(originalSetView){
 setView=function(view){const url=location.href,state=history.state;const result=originalSetView(view);restoreNavigationLocation(url,state);scheduleSync();queueMicrotask(()=>{if(typeof updateDetails==='function')updateDetails();});return result;};
}
if(originalRender){
 render=function(){const url=location.href,state=history.state;const result=originalRender();restoreNavigationLocation(url,state);scheduleSync();return result;};
}
window.addEventListener('popstate',event=>{
 const state=event.state;
 if(!state?.boatEdgeNav||!state.snapshot)return;
 restoring=true;
 position=state.position;current=state.snapshot;
 const v=current;
 s.date=v.date;s.venue=v.venue;s.race=v.race;
 if(originalSetView)originalSetView(v.view);
 if(v.view==='card'&&typeof setRaceCardPane==='function')setRaceCardPane(v.pane==='rates'?'rates':'card');
 if(v.view==='forecast'&&typeof setForecastPane==='function')setForecastPane('prediction');
 if(originalRender)originalRender();
 // popstate already restored the destination entry. Avoid an identical
 // replaceState during back/forward to preserve WebKit's history quota.
 if(history.state!==state&&JSON.stringify(history.state)!==JSON.stringify(state))
  history.replaceState(state,'',location.href);
 restoring=false;
});
// The only back control is in index.html; browser history takes precedence.
back?.addEventListener('click',event=>{
 if(position>0){event.stopImmediatePropagation();history.back();}
},true);
document.querySelectorAll('.race-detail-shortcuts').forEach(node=>node.remove());
const details=document.createElement('nav');details.className='race-detail-shortcuts';
details.setAttribute('aria-label','選択レースの情報');
for(const [label,view] of [['予想','forecast'],['出走表','card'],['展示・直前','exhibit'],['結果','result']]){
 const b=document.createElement('button');b.type='button';b.textContent=label;b.dataset.raceView=view;
 b.addEventListener('click',()=>{
  if(typeof setView!=='function'||typeof render!=='function')return;
  if(view==='forecast'&&typeof setForecastPane==='function')setForecastPane('prediction');
  if(view==='card'&&typeof setRaceCardPane==='function')setRaceCardPane('card');
  setView(view);
  render();
  document.querySelector(view==='forecast'?'#forecast':view==='result'?'#resultSection':'#raceDataSection')?.scrollIntoView({block:'start'});
 });
 details.append(b);
}
document.querySelector('.active-race-strip')?.insertAdjacentElement('afterend',details);
const updateDetails=()=>{
 const isHome=activeView==='home';
 const isReview=activeView==='review';
 const showRaceControls=!isHome&&!isReview;
 // Keep home and verification focused: race-specific controls belong only to race pages.
 const strip=document.querySelector('.active-race-strip');
 if(strip)strip.hidden=!showRaceControls;
 details.hidden=!showRaceControls;
 details.querySelectorAll('button').forEach(b=>{
   const selected=b.dataset.raceView===activeView;
   b.setAttribute('aria-current',String(selected));
   b.classList.toggle('on',selected);
  });
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
// On narrow iPhones the four race tabs must fit within the viewport without
// forcing horizontal scrolling or making the touch targets too short.
const mobileStyles=document.createElement('style');
mobileStyles.textContent='@media(max-width:480px){.race-detail-shortcuts{width:100%;max-width:100%;padding:0 8px 9px;gap:4px;box-sizing:border-box;min-width:0}.race-detail-shortcuts button{flex:1 1 0;min-width:0;min-height:44px;padding:8px 2px;font-size:clamp(10px,2.9vw,12px);line-height:1.25;white-space:normal;overflow-wrap:anywhere}.active-race-strip{min-width:0}.active-race-strip strong{overflow-wrap:anywhere}}';
document.head.append(mobileStyles);
})();
