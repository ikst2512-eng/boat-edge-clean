const {chromium}=require('playwright');
(async()=>{
 const b=await chromium.launch();
 try{
  const page=await b.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  await page.goto('https://boat-edge-clean.onrender.com/',{waitUntil:'domcontentloaded',timeout:60000});
  await page.waitForSelector('#predictionRows',{timeout:30000});
  const actual=await page.evaluate(()=>{
   const tickets=['1-2-3','1-3-2','2-1-3','2-3-1','3-1-2','3-2-1','1-2-4','1-4-2','2-1-4','2-4-1'];
   selectedPredictionMode='research';
   predictionModes.research={tickets,probabilities:{},odds:Object.fromEntries(tickets.map((x,i)=>[x,10+i]))};
   applyPredictionMode();
   return Array.from(document.querySelectorAll('#predictionRows .prediction-row'),row=>({ticket:row.querySelector('.prediction-ticket')?.textContent,odds:row.querySelector('.prediction-odds')?.textContent}));
  });
  if(actual.length!==10)throw Error('Ten tickets missing '+actual.length);
  for(let i=0;i<10;i++){
   if(actual[i].ticket!==['1-2-3','1-3-2','2-1-3','2-3-1','3-1-2','3-2-1','1-2-4','1-4-2','2-1-4','2-4-1'][i])throw Error('rank mismatch '+i);
   if(!actual[i].odds.includes((10+i)+'倍'))throw Error('odds mismatch '+i);
  }
  console.log('Rendered mobile DOM 10 ticket/odds pairs PASS');
 }finally{await b.close()}
})().catch(e=>{console.error(e);process.exit(1)});
