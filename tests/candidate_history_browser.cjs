// Standalone candidate archive browser regression, no Render/official live access.
const { chromium } = require('playwright');

(async () => {
 const browser = await chromium.launch({headless:true});
 try {
  const page = await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const errors=[],renderCalls=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{
   if(request.url().includes('boat-edge-clean.onrender.com'))renderCalls.push(request.url());
  });
  // Expanded raw four-mode files are optional; test immutable candidate manifest,
  // not external network availability or an alleged formal accuracy result.
  await page.route('https://raw.githubusercontent.com/**',route=>
   route.fulfill({status:404,contentType:'application/json',body:'{}'}));
  const url='http://127.0.0.1:8765/candidates.html?date=2026-11-08';
  const response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:20000});
  if(response?.status()!==200)throw Error('candidate_static_page_http_'+response?.status());
  await page.waitForFunction(()=>document.querySelector('#candidateStatus')?.textContent?.startsWith('保存候補 '));
  const shortlist=await page.evaluate(()=>({
    count:document.querySelectorAll('#candidateCards > details.candidate-history-card').length,
    selected:document.querySelector('#candidateHistoryFilters [data-candidate-filter="priority"]')?.getAttribute('aria-pressed'),
    text:document.querySelector('#candidateStatus')?.textContent||''
  }));
  if(shortlist.selected!=='true'||shortlist.count>10||!shortlist.text.includes('研究優先 '))
   throw Error('research_shortlist_not_default_'+JSON.stringify(shortlist));
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
  const review=await page.locator('#candidateCards > details').first().locator('.candidate-detail').innerText();
  if(!review.includes('購入判断：見送り')||
     !review.includes('2コースの壁・逃がし率')||
     !review.includes('風・波・水面')||
     !review.includes('初回保存証明・正式予想認定'))
   throw Error('candidate_evidence_hold_missing_'+review.slice(0,500));
  if(!opened.open||!opened.saved?.includes('1-2-4')||  if(!opened.open||!opened.saved?.includes('1-2-4')||
      !opened.links.some(x=>x.includes('screen=forecast'))||
      !opened.links.some(x=>x.includes('screen=result')))
   throw Error('candidate_detail_missing_'+JSON.stringify(opened));
  const dateInput=page.locator('#candidateHistoryDate');
  await dateInput.fill('2026-11-07');
  await dateInput.dispatchEvent('change');
  await page.waitForFunction(()=>new URL(location.href).searchParams.get('date')==='2026-11-07'&&
    document.querySelector('#candidateStatus')?.textContent?.startsWith('保存候補 '));
  await page.locator('#candidateHistoryFilters [data-candidate-filter="all"]').click();
  const yesterday=await page.locator('#candidateCards > details.candidate-history-card').count();
  if(yesterday<=6)throw Error('historical_day_candidate_rows_missing_'+yesterday);
  if(errors.length||renderCalls.length)throw Error('browser_error_or_render_dependency_'+JSON.stringify({errors,renderCalls}));
  console.log('CANDIDATE_STATIC_BROWSER_PASS '+JSON.stringify({nov8:first.count,nov7:yesterday,saved_forecast:true,shortlist:shortlist.count,full_history_preserved:true,results_and_links:true,no_render_dependency:true}));
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
