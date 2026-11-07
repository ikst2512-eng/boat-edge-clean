((csvText, date) => {
  // Pure research-only parser: post-race observations MUST NOT be supplied to T-12 predictions.
  const parsed = [];
  let row = [], value = "", quoted = false;
  for (let i = 0; i < csvText.length; i++) {
    const c = csvText[i];
    if (quoted) {
      if (c === '"') { if (csvText[i+1] === '"') {value += '"'; i++;} else quoted = false; }
      else value += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(value); value = ""; }
    else if (c === '\n') { row.push(value.replace(/\r$/, "")); parsed.push(row); row=[]; value=""; }
    else value += c;
  }
  if (row.length || value) {row.push(value); parsed.push(row);}
  const headers = parsed.shift() || [];
  const required = ["レースコード", "1着_艇番", "決まり手", "風速(m)", "風向", "波の高さ(cm)"];
  for (let j=1;j<=6;j++) {
    required.push(j+"コース_艇番", j+"コース_F");
  }
  required.push("1コース_スタートタイミング");
  if (required.some(k=>!headers.includes(k))) throw Error("MISSING_CSV_SCHEMA "+date);
  const records = parsed.filter(x=>x.some(v=>v!=="")).map(a=>Object.fromEntries(headers.map((h,i)=>[h,a[i]??""])));
  const out = {rows:records.length,valid:0,excluded:{},group:{},bad_waves:0,missing_st1:0};
  const seen = new Set();
  for (const r of records) {
    const code=(r["レースコード"]||"").trim();
    const courses=Array.from({length:6},(_,j)=>Number((r[(j+1)+"コース_艇番"]||"").trim()));
    const winner=Number(r["1着_艇番"]);
    const rawSpeed=(r["風速(m)"]||"").trim(), wind=Number(rawSpeed);
    const method=(r["決まり手"]||"").replace(/\s/g,"");
    let problem=null;
    if(!/^\d{12}$/.test(code)||!code.startsWith(date.replaceAll("/",""))||
       !((+code.slice(8,10))>=1&&(+code.slice(8,10))<=24)||
       !((+code.slice(10,12))>=1&&(+code.slice(10,12))<=12)) problem="invalid_code";
    else if(seen.has(code)) problem="duplicate_code";
    else if(courses.some(v=>v<1||v>6)||courses.slice().sort((a,b)=>a-b).join(",")!=="1,2,3,4,5,6"||!courses.includes(winner)) problem="invalid_course";
    else if(!rawSpeed||!Number.isFinite(wind)||wind<0||wind>40||!Number.isInteger(wind)) problem="invalid_wind";
    else if(!["逃げ","差し","まくり","まくり差し","抜き","恵まれ"].includes(method)) problem="invalid_method";
    seen.add(code);
    if(problem) {out.excluded[problem]=(out.excluded[problem]||0)+1;continue;}
    out.valid++;
    const venue=code.slice(8,10),band=wind<=2?"0-2":wind<=4?"3-4":"5+";
    const course=courses.indexOf(winner)+1, key=venue+"/"+band;
    const a=out.group[key]??(out.group[key]={n:0,c1:0,escape:0,courses:{},methods:{},cross:{},wave_total:0,wave_n:0,st1_total:0,st1_n:0,wind_direction_raw:{},f_races:0});
    a.n++;a.c1+=(course===1);a.escape+=(method==="逃げ");
    a.courses[course]=(a.courses[course]||0)+1;
    a.methods[method]=(a.methods[method]||0)+1;
    const cm=course+"C_"+method;a.cross[cm]=(a.cross[cm]||0)+1;
    const direction=(r["風向"]||"").trim();
    a.wind_direction_raw[direction]=(a.wind_direction_raw[direction]||0)+1;
    const wave=(r["波の高さ(cm)"]||"").trim();
    if(/^\d+(?:\.\d+)?$/.test(wave)){a.wave_total+=+wave;a.wave_n++;}
    else out.bad_waves++;
    const st=(r["1コース_スタートタイミング"]||"").trim();
    if(/^-?\d+(?:\.\d+)?$/.test(st)){a.st1_total+=+st;a.st1_n++;}
    else out.missing_st1++;
    if(Array.from({length:6},(_,i)=>r[(i+1)+"コース_F"]).some(v=>(v||"").trim()==="F")) a.f_races++;
  }
  if(out.valid+Object.values(out.excluded).reduce((a,b)=>a+b,0)!==out.rows) throw Error("ACCOUNTING_FAILURE "+date);
  return out;
})
