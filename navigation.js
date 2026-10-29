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
})();