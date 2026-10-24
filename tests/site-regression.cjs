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
const tickets=['1-2-3','1-3-2','2-1-3','2-3-1','3-1-2','3-2-1','1-2-4','1-4-2','2-1-4','2-4-1'];
for(const [rank,expected] of [[1,[true,true,true]],[3,[true,true,true]],[4,[false,true,true]],[5,[false,true,true]],[6,[false,false,true]],[10,[false,false,true]],[0,[false,false,false]]]){
 const r=classify(tickets,rank?tickets[rank-1]:'6-5-4');
 assert.equal(r.rank,rank);
 assert.deepEqual([r.top3,r.top5,r.top10],expected);
}
assert.equal(classify(tickets,'1-2-5').rank,0);
const key='20261023-04-10';
const base='https://www.boatrace.jp/owpc/pc/race/raceresult?hd=20261023&jcd=04&rno=10';
assert.equal(official(base,key),true);
for(const source of [
 base.replace('https:','http:'),base.replace('www.boatrace.jp','www.boatrace.jp.evil.test'),
 base.replace('hd=20261023','hd=20261024'),base.replace('jcd=04','jcd=05'),
 base.replace('rno=10','rno=11'),base.replace('raceresult','racelist'),
 'https://example.com','not-a-url'
])assert.equal(official(source,key),false,source);
for(const literal of ['FIRST_ADD_UNCONFIRMED','SNAPSHOT_CHANGED_SINCE_FIRST_ADD','FREEZE_TIME_NOT_PROVEN','results_seen!==false','unlock!==false','scoring!==false'])assert.ok(script.includes(literal),'missing proof guard: '+literal);
assert.equal((html.match(/id="venues"/g)||[]).length,1);
assert.ok(html.includes("const names=['桐生'"));
console.log('PASS: JS syntax, Top3/5/10 boundaries, official URL validation, predeadline guards, 24-venue entry point');
