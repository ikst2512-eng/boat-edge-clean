(()=>{'use strict';
const nav=document.querySelector('.site-global-nav');
if(!nav)return;
const params=location.search;
nav.innerHTML='<a href="/review">検証</a><a href="/selection">購入候補</a>';
nav.setAttribute('aria-label','検証と購入候補');
nav.classList.add('compact-nav');
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
const snapshot=()=>({date:s.date,venue:s.venue,race:s.race,view:activeView});
const key=p=>[p.date,p.venue,p.race,p.view].join('|');
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
const refresh=()=>{back.disabled=position===0;back.setAttribute('aria-disabled',String(position===0));};
if(originalSetView){
 setView=function(view){const result=originalSetView(view);sync();return result;};
}
if(originalRender){
 render=function(){const result=originalRender();sync();return result;};
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
 restoring=false;refresh();
});
back.addEventListener('click',()=>{if(position>0)history.back();else location.assign('/');});
refresh();
const browserStyle=document.createElement('style');
browserStyle.textContent='.race-browser-toolbar{display:flex;justify-content:space-between;gap:8px;max-width:900px;margin:0 auto;padding:8px 14px}.race-browser-toolbar button,.race-browser-toolbar a{font-size:14px;font-weight:800;border:1px solid #cbd9e8;border-radius:9px;background:#fff;color:#174066;padding:9px 14px;text-decoration:none;min-height:40px}.race-browser-toolbar button:disabled{opacity:.5}.race-browser-toolbar a{text-align:center}@media(max-width:420px){.race-browser-toolbar button,.race-browser-toolbar a{flex:1}}';
document.head.append(browserStyle);
})();