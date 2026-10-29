(()=>{'use strict';
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
})();