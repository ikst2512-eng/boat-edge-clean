/* Read-only, exploratory scenario re-rank. NEVER a formal/frozen forecast.
 * Uses the same static 1,000-race lane priors and beta 0.4 weighting
 * as research_model.py, but remaps position priors to user-chosen boat entry.
 * This positional transfer has NOT been calibrated against course changes.
 */
(function(root, factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.BoatEntryScenario=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const COUNTS="59,60,36,28,51,31,48,24,34,29,21,15,24,19,19,12,3,4,10,9,21,17,11,8,12,11,9,3,9,5,4,7,4,5,1,4,1,1,1,2,13,19,12,12,11,8,2,2,8,4,4,3,6,7,4,2,2,2,2,1,7,8,8,6,2,10,1,5,7,4,5,5,7,3,6,4,6,4,2,6,4,1,6,7,6,3,2,1,6,1,0,5,7,5,3,1,4,5,1,0,2,4,1,2,3,1,1,0,2,0,1,2,1,3,1,2,3,0,1,0".split(',').map(Number);
  const ROWS=[];
  for(let a=1;a<=6;a++)for(let b=1;b<=6;b++)for(let c=1;c<=6;c++){
    if(a!==b&&a!==c&&b!==c)ROWS.push([a,b,c]);
  }
  const WINS=Array.from({length:6},()=>0);
  ROWS.forEach((row,i)=>WINS[row[0]-1]+=COUNTS[i]);
  if(ROWS.length!==120||COUNTS.length!==120||COUNTS.reduce((a,b)=>a+b,0)!==1000)throw Error('scenario_prior_invalid');
  function validateEntry(entry){
    if(!Array.isArray(entry)||entry.length!==6||entry.some(n=>!Number.isInteger(n)||n<1||n>6)||new Set(entry).size!==6)throw Error('entry_must_be_six_unique_boats');
    return entry.slice();
  }
  function rank(rates,entry){
    const order=validateEntry(entry);
    if(!Array.isArray(rates)||rates.length!==6||rates.some(n=>typeof n!=='number'||!Number.isFinite(n)||n<=0||n>=20))throw Error('invalid_six_national_rates');
    const mean=rates.reduce((a,b)=>a+b,0)/6;
    const weights=order.map((boat,i)=>(WINS[i]+12)*Math.exp(0.4*(rates[boat-1]-mean)));
    const total=weights.reduce((a,b)=>a+b,0);
    const ranked=ROWS.map((courses,i)=>{
      const first=courses[0]-1;
      const p=(weights[first]/total)*(COUNTS[i]+0.5)/(WINS[first]+10);
      return {combo:courses.map(course=>order[course-1]).join('-'),p:p*100};
    });
    const mass=ranked.reduce((v,row)=>v+row.p,0);
    if(!Number.isFinite(mass)||Math.abs(mass-100)>1e-8)throw Error('scenario_mass_invalid');
    ranked.sort((a,b)=>b.p-a.p||a.combo.localeCompare(b.combo,'en'));
    return {tickets:ranked.slice(0,10),entry:order,model:'entry-position-transfer-beta0.4-research',
      validated:false,formal:false,forecast_usable:false,confidence_calibrated:false,
      assumptions:'1,000-race boat-index prior remapped by course; not experimentally verified'};
  }
  return Object.freeze({rank,validateEntry});
});