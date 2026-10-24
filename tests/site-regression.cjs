// Regression checks for the exact production validators in index.html.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('index.html','utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script,'inline application script must exist');
new vm.Script(script,{filename:'index.html'});
function extract(name){
 const line=script.split('\n').find(l=>l.startsWith('function '+name+'('));
 assert.ok(line,'production validator '+name+' missing');
 return vm.runInNewContext(line+';'+name,{URL});
}
const classify=extract('classifyPredictionMatch'),official=extract('isOfficialResultSource');
const ticketFns=vm.runInNewContext([script.match(/const validTicket=[^\n]+/)[0],script.split('\n').find(l=>l.startsWith('function verifiedTicketArray(')),'({validTicket,verifiedTicketArray})'].join('\n'));
const validTicket=ticketFns.validTicket,verifiedTickets=ticketFns.verifiedTicketArray;
const allTen=['1-2-3','1-2-4','1-2-5','1-2-6','1-3-2','1-3-4','1-3-5','1-3-6','1-4-2','1-4-3'];
assert.equal(verifiedTickets(allTen),true);
assert.equal(verifiedTickets(allTen.slice(0,9)),false);
assert.equal(verifiedTickets([...allTen.slice(0,9),allTen[0]]),false);
for(const invalid of ['1-1-2','0-1-2','1-7-2','1-2','1-2-3-4'])assert.equal(validTicket(invalid),false,invalid);
const tickets=['1-2-3','1-3-2','2-1-3','2-3-1','3-1-2','3-2-1','1-2-4','1-4-2','2-1-4','2-4-1'];
for(const [rank,expected] of [[1,[true,true,true]],[3,[true,true,true]],[4,[false,true,true]],[5,[false,true,true]],[6,[false,false,true]],[10,[false,false,true]],[0,[false,false,false]]]){
 const r=classify(tickets,rank?tickets[rank-1]:'6-5-4');
 assert.equal(r.rank,rank);
 assert.deepEqual([r.top3,r.top5,r.top10],expected);
}
assert.equal(classify(tickets,'1-2-5').rank,0);
// Stored 2026-10-23 prediction ticket order compared with confirmed results.
// This tests comparison only, NOT first-Git-add proof or formal scoring.
for(const sample of [
 {key:'20261023-04-10',combo:'1-2-5',rank:0,tickets:['1-2-6','1-6-2','1-2-3','1-2-4','1-4-2','2-1-6','2-1-4','2-1-3','2-6-1','6-1-2']},
 {key:'20261023-06-10',combo:'3-1-2',rank:0,tickets:['1-4-6','1-6-4','1-6-5','1-5-6','1-4-5','6-1-4','4-1-6','4-1-5','6-1-5','6-4-1']},
 {key:'20261023-11-11',combo:'1-3-2',rank:4,tickets:['1-3-4','1-4-3','1-3-6','1-3-2','1-2-3','3-1-4','3-1-6','3-1-2','4-1-3','3-4-1']}
]){
 const verdict=classify(sample.tickets,sample.combo);
 assert.equal(verdict.rank,sample.rank,sample.key);
 assert.equal(verdict.top3,false,sample.key);
 assert.equal(verdict.top5,sample.rank===4,sample.key);
 assert.equal(verdict.top10,sample.rank===4,sample.key);
}
const resultValidator=vm.runInNewContext([
 script.split('\n').find(l=>l.startsWith('function isOfficialResultSource(')),
 script.split('\n').find(l=>l.startsWith('function isVerifiedResult(')),
 'isVerifiedResult'
].join('\n'),{URL});
const now=Date.parse('2026-10-23T18:00:00+09:00');
const validResult={schema_version:'boat-edge-site-result-v109',race_key:'20261023-04-10',status:'confirmed',finish_order:[1,2,5],trifecta:'1-2-5',trifecta_payout_yen_per_100:1500,fetched_at:'2026-10-23T15:30:00+09:00',source:'https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261023&jcd=04&rno=10'};
assert.equal(resultValidator(validResult,'20261023-04-10',now),true);
assert.equal(resultValidator(validResult,'20261023-04-10',now,'15:14'),true);
assert.equal(resultValidator({...validResult,fetched_at:'2026-10-23T15:13:59+09:00'},'20261023-04-10',now,'15:14'),false);
assert.equal(resultValidator(validResult,'20261023-04-10',now,'invalid'),false);
for(const patch of [
 {finish_order:[1,1,5]},{finish_order:[1,2,7]},{trifecta:'1-5-2'},
 {trifecta_payout_yen_per_100:-100},{trifecta_payout_yen_per_100:'1500'},
 {fetched_at:'2026-10-22T14:00:00Z'},{fetched_at:'2026-10-24T00:00:00+09:00'},
 {source:validResult.source+'&jcd=05'},{race_key:'20261023-04-11'},
 {status:'provisional'},{schema_version:'unverified'}
])assert.equal(resultValidator({...validResult,...patch},'20261023-04-10',now),false,JSON.stringify(patch));
const key='20261023-04-10';
const base='https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261023&jcd=04&rno=10';
assert.equal(official(base,key),true);
for(const source of [
 base.replace('https:','http:'),base.replace('www.boatrace.jp','www.boatrace.jp.evil.test'),
 base.replace('hd=20261023','hd=20261024'),base.replace('jcd=04','jcd=05'),
 base.replace('rno=10','rno=11'),base+'&rno=11',base+'&hd=20261024',base.replace('raceresult','racelist'),
 'https://example.com','not-a-url'
])assert.equal(official(source,key),false,source);
for(const literal of ['FIRST_ADD_UNCONFIRMED','SNAPSHOT_CHANGED_SINCE_FIRST_ADD','FREEZE_TIME_NOT_PROVEN','results_seen!==false','unlock!==false','scoring!==false'])assert.ok(script.includes(literal),'missing proof guard: '+literal);
assert.equal((html.match(/id="venues"/g)||[]).length,1);
const venueDeclaration=script.match(/const names=\[([^\]]+)\]/);
assert.ok(venueDeclaration,'24 venue names must be declared');
const venues=venueDeclaration[1].split(',').map(s=>s.trim().replace(/^'|'$/g,''));
assert.equal(venues.length,24,'all 24 venues must be present');
assert.equal(new Set(venues).size,24,'venue names must be unique');
assert.equal(venues[0],'桐生');
assert.equal(venues[23],'大村');
// Every statically referenced element must exist, and HTML IDs must not collide.
const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
assert.equal(new Set(ids).size,ids.length,'duplicate HTML element ID');
for(const match of script.matchAll(/getElementById\('([^']+)'\)/g)){
 assert.ok(ids.includes(match[1]),'missing HTML element #'+match[1]);
}
assert.ok(script.includes("if(activeView==='card'||activeView==='exhibit')loadRaceData(true);else if(activeView==='forecast'"),'active card and exhibition must refresh on timer');
console.log('PASS: JS syntax, Top3/5/10 boundaries, official URL validation, predeadline guards, 24-venue entry point');
