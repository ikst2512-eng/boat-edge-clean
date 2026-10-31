const {chromium}=require('playwright');
(async()=>{
 const b=await chromium.launch();
 try{
  const page=await b.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const tickets=['1-2-3','1-3-2','2-1-3','2-3-1','3-1-2','3-2-1','1-2-4','1-4-2','2-1-4','2-4-1'];
  await page.goto('https://boat-edge-clean.onrender.com/?date=2026-10-31&venue=2&race=1',{waitUntil:'domcontentloaded',timeout:60000});
  await page.waitForSelector('#predictionRows',{state:'attached'});
  const result=await page.evaluate(async tickets=>{
    const key='20261031-02-01';
    s.date='2026-10-31';s.venue=1;s.race=1;
    setView('forecast');
    selectedPredictionMode='research';
    predictionModes.research={tickets,probabilities:{},odds:{}};
    applyPredictionMode();
    const token=(window.predictionRequestId||0)+1;window.predictionRequestId=token;
    const live=await fetch('/api/odds?hd=20261031&jcd=02&rno=1',{cache:'no-store'});
    if(live.status!==200)return {status:live.status,unavailable:true};
    const data=await live.json();
    if(!data.ok||Object.keys(data.odds||{}).length!==120)throw Error('not 120 odds');
    await loadTicketOdds(key,token);
    const rows=Array.from(document.querySelectorAll('#predictionRows .prediction-row'));
    return {status:live.status,count:rows.length,rows:rows.map(r=>({ticket:r.querySelector('.prediction-ticket')?.textContent,odds:r.querySelector('.prediction-odds')?.textContent})),expected:tickets.map(t=>data.odds[t])};
  },tickets);
  if(result.unavailable)throw Error('LIVE_ODDS_UNAVAILABLE_HTTP_'+result.status);
  if(result.count!==10)throw Error('Count mismatch '+result.count);
  result.rows.forEach((row,i)=>{
    if(row.ticket!==tickets[i])throw Error('Ticket rank mismatch '+i);
    if(!row.odds.includes(result.expected[i].toLocaleString('ja-JP')+'倍'))throw Error('Real odds mismatch '+i);
  });
  console.log('REAL_ODDS_10_DOM_MATCH PASS');
 }finally{await b.close()}
})().catch(e=>{console.error(e);process.exit(1)});
