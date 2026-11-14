// Standalone candidate archive browser regression, no Render/official live access.
const { chromium } = require('playwright');

(async () => {
 const browser = await chromium.launch({headless:true});
 try {
  const page = await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const errors=[],renderCalls=[],rawGithubCalls=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{
   if(request.url().includes('boat-edge-clean.onrender.com'))renderCalls.push(request.url());
   if(request.url().includes('raw.githubusercontent.com'))rawGithubCalls.push(request.url());
  });
  // Archived four-mode detail is bundled with Pages. A cross-origin raw
  // fetch must not be required just to re-open a saved prediction.
  await page.route('https://raw.githubusercontent.com/**',route=>route.abort());
  const url='http://127.0.0.1:8765/candidates.html?date=2026-11-08';
  const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:20000});
  if(response?.status()!==200)throw Error('candidate_static_page_http_'+response?.status());
  await page.waitForFunction(()=>document.querySelector('#candidateStatus')?.textContent?.startsWith('保存候補 '));
  const initial=await page.evaluate(()=>({
    count:document.querySelectorAll('#candidateCards > details.candidate-history-card').length,
    selected:document.querySelector('#candidateHistoryFilters [data-candidate-filter="all"]')?.getAttribute('aria-pressed'),
    text:document.querySelector('#candidateStatus')?.textContent||''
  }));
  if(initial.selected!=='true'||initial.count<=6||
     !initial.text.includes('保存候補 '+initial.count+'件')||
     !initial.text.includes('表示 '+initial.count+'件'))
   throw Error('saved_history_not_default_'+JSON.stringify(initial));
  // The research top-10 remains an explicit optional filter.
  await page.locator('#candidateHistoryFilters [data-candidate-filter="priority"]').click();
  const shortlist=await page.evaluate(()=>({
    count:document.querySelectorAll('#candidateCards > details.candidate-history-card').length,
    selected:document.querySelector('#candidateHistoryFilters [data-candidate-filter="priority"]')?.getAttribute('aria-pressed')
  }));
  if(shortlist.selected!=='true'||shortlist.count>10||shortlist.count>initial.count)
   throw Error('opt_in_research_shortlist_invalid_'+JSON.stringify(shortlist));
  await page.locator('#candidateHistoryFilters [data-candidate-filter="all"]').click();
  const first=await page.evaluate(()=>{
   const cards=[...document.querySelectorAll('#candidateCards > details.candidate-history-card')];
   return {count:cards.length,unique:new Set(cards.map(x=>x.dataset.raceCode)).size,
    status:document.getElementById('candidateStatus').textContent,
    first:cards[0]?.querySelector('summary')?.textContent};
  });
  if(first.count<=6||first.count!==first.unique||!first.status.includes('保存候補 '+first.count+'件')||
     shortlist.count>first.count)throw Error('candidate_count_or_duplicates_'+JSON.stringify({first,shortlist}));
  await page.locator('#candidateCards > details').first().locator('summary').click();
  const opened=await page.evaluate(()=>{
   const card=document.querySelector('#candidateCards > details');
   return {open:card?.open,saved:card?.querySelector('.candidate-tickets')?.textContent,
    links:[...card.querySelectorAll('.candidate-links a')].map(x=>x.href)};
  });
  // The first saved candidate (202611080501) has no historical four-mode
  // file; it must remain visible without inventing four new mode records.
  const absent=page.locator('#candidateCards > details[data-race-code="202611080501"]');
  if(await absent.count()!==1)throw Error('candidate_with_missing_modes_disappeared');
  await page.waitForFunction(()=>
    document.querySelector('#candidateCards > details[data-race-code="202611080501"] .candidate-modes')?.textContent?.includes('4モードの保存予想はありません。'),
    null,{timeout:12000});
  // A different genuinely archived race has all 4 modes. It must load
  // from the same-origin Pages copy even when GitHub Raw is blocked.
  const archivedCode='202611080101';
  const archived=page.locator('#candidateCards > details[data-race-code="'+archivedCode+'"]');
  if(await archived.count()!==1)throw Error('archived_four_mode_candidate_missing_'+archivedCode);
  await archived.locator('summary').click();
  await page.waitForFunction(code=>
    document.querySelectorAll('#candidateCards > details[data-race-code="'+code+'"] .candidate-modes .candidate-mode').length===4,
    archivedCode,{timeout:15000});
  const modeCount=await archived.locator('.candidate-modes .candidate-mode').count();
  if(modeCount!==4)throw Error('saved_four_modes_not_rendered_'+modeCount);
  const review=await page.locator('#candidateCards > details').first().locator('.candidate-detail').innerText();
  if(!review.includes('研究入力の紐付け：'))throw Error('research_source_link_not_displayed');
  if(!review.includes('購入判断：見送り')||
     !review.includes('2コースの壁・逃がし率')||
     !review.includes('風・波・水面')||
     !review.includes('初回保存証明・正式予想認定'))
   throw Error('candidate_evidence_hold_missing_'+review.slice(0,500));
  if(!opened.open||!opened.saved?.includes('1-2-4')||
      !opened.links.some(x=>x.includes('screen=forecast'))||
      !opened.links.some(x=>x.includes('screen=result')))
   throw Error('candidate_detail_missing_'+JSON.stringify(opened));
  const dateInput=page.locator('#candidateHistoryDate');
  await dateInput.fill('2026-11-07');
  await dateInput.dispatchEvent('change');
  await page.waitForFunction(()=>new URL(location.href).searchParams.get('date')==='2026-11-07'&&
    document.querySelector('#candidateStatus')?.textContent?.startsWith('保存候補 '));
  if(await page.locator('#candidateHistoryFilters [data-candidate-filter="all"]').getAttribute('aria-pressed')!=='true')
    throw Error('previous_day_restricted_history_filter');
  const yesterday=await page.locator('#candidateCards > details.candidate-history-card').count();
  if(yesterday<=6)throw Error('historical_day_candidate_rows_missing_'+yesterday);
  if(errors.length||renderCalls.length||rawGithubCalls.length)throw Error('archive_external_dependency_'+JSON.stringify({errors,renderCalls,rawGithubCalls}));
  console.log('CANDIDATE_STATIC_BROWSER_PASS '+JSON.stringify({nov8:first.count,nov7:yesterday,saved_forecast:true,shortlist:shortlist.count,full_history_preserved:true,results_and_links:true,four_modes_same_origin:true,no_render_dependency:true}));
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
