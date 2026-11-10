// RESEARCH-ONLY, OFFLINE Git first-add evidence internal-consistency check.
// NO GitHub network, no source file writes, no Cloudflare deployment or dispatch.
// Operator-provided manifests and Git metadata are untrusted: even a PASS
// never proves server first-receipt, Git parent-tree ancestry or formal T-12.
import {createHash} from 'node:crypto';

export const FIRST_ADD_LAB_SCHEMA='BOAT_EDGE_FIRST_ADD_SOURCE_MANIFEST_LAB_V1';
const REPO='ikst2512-eng/boat-edge-clean';
const SHA=/^[0-9a-f]{40}$/;
const SHA256=/^[0-9a-f]{64}$/;
const CODE=/^20[0-9]{10}$/;
const JST=/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?\+09:00$/;
const modes=['hit','balance','hole','narrow'];
const expectedWorkflow={clean:'clean-prospective.yml',four_mode:'four-mode-prospective-capture.yml'};
const isObj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
function clock(s){
  if(typeof s!=='string'||!JST.test(s))return null;
  const n=Date.parse(s);
  return Number.isFinite(n)?n:null;
}
function idFromPath(path,kind){
  if(typeof path!=='string')return null;
  const re=kind==='clean'?/^prospective_predictions\/(20[0-9]{10})\.json$/
    : /^four_mode_forecasts\/(20[0-9]{10})\.json$/;
  const m=re.exec(path);
  if(!m||!CODE.test(m[1]))return null;
  const c=m[1],date=c.slice(0,8),venue=Number(c.slice(8,10)),race=Number(c.slice(10,12));
  if(venue<1||venue>24||race<1||race>12)return null;
  const d=new Date(Date.UTC(Number(date.slice(0,4)),Number(date.slice(4,6))-1,Number(date.slice(6,8))));
  if(Number.isNaN(d.getTime())||d.toISOString().slice(0,10).replaceAll('-','')!==date)return null;
  return c;
}
function blob1(raw){
  const bytes=Buffer.from(raw,'utf8');
  return createHash('sha1').update(Buffer.from('blob '+bytes.length+'\0')).update(bytes).digest('hex');
}
function digest256(raw){return createHash('sha256').update(Buffer.from(raw,'utf8')).digest('hex')}
function failSafeResult(issues,rows,mode){
  return {
    schema:FIRST_ADD_LAB_SCHEMA, publisher:mode??null,
    records_checked:rows, local_content_consistency_pass:issues.length===0,
    issue_count:issues.length, issues:issues.slice(0,30),
    github_manifest_authenticity_independently_proven:false,
    git_first_add_parent_tree_independently_proven:false,
    remote_server_first_receipt_independently_proven:false,
    official_beforeinfo_six_boats_proven:false,
    odds_120_combinations_proven:false,
    official_t_minus_12_proven:false,
    cross_provider_recovery_release_approved:false,
  };
}
export function auditLocalFirstAddEvidence(input){
  if(!isObj(input))throw Error('first_add_lab_input_invalid');
  const issues=[];const bad=x=>{if(issues.length<30)issues.push(x)};
  if(input.schema!==FIRST_ADD_LAB_SCHEMA)bad('schema_invalid');
  if(input.repository!==REPO||input.branch!=='main')bad('wrong_repo_or_branch');
  const kind=input.publisher;
  if(!Object.hasOwn(expectedWorkflow,kind)){bad('publisher_invalid');return failSafeResult(issues,0,kind)}
  const run=input.github_run,commit=input.commit;
  if(!isObj(run)||!Number.isSafeInteger(run.id)||run.id<=0||
      run.workflow_path!=='.github/workflows/'+expectedWorkflow[kind]||
      run.head_branch!=='main'||!['schedule','workflow_dispatch'].includes(run.event)||
      run.status!=='completed'||run.conclusion!=='success')
      bad('github_run_claim_invalid');
  if(input.reported_dispatch_run_id!==undefined&&
      (run?.event!=='workflow_dispatch'||input.reported_dispatch_run_id!==run?.id))
      bad('reported_dispatch_id_mismatch');
  const committed=clock(commit?.committed_at_jst);
  if(!isObj(commit)||!SHA.test(commit.sha)||!SHA.test(commit.parent_sha)||
      commit.sha===commit.parent_sha||committed===null)bad('commit_claim_invalid');
  const records=input.records;
  if(!Array.isArray(records)||records.length<1||records.length>150){
    bad('record_roster_missing_or_unbounded');
    return failSafeResult(issues,0,kind);
  }
  if(!Array.isArray(input.claimed_added_paths)||input.claimed_added_paths.length!==records.length||
      !input.claimed_added_paths.every(x=>typeof x==='string')||
      new Set(input.claimed_added_paths).size!==records.length)
    bad('claimed_first_add_roster_invalid');
  const seen=new Set(), paths=[];
  for(const [i,row] of records.entries()){
    const code=idFromPath(row?.path,kind);
    if(!isObj(row)||!code||row.claimed_git_status!=='added'){
      bad('record_'+i+'_path_or_addition_invalid');continue;
    }
    if(seen.has(row.path)){bad('record_'+i+'_duplicate_path');continue}
    seen.add(row.path);paths.push(row.path);
    if(typeof row.original_git_blob_utf8!=='string'||row.original_git_blob_utf8.length>50000){
      bad('record_'+i+'_blob_missing_or_oversize');continue;
    }
    const raw=row.original_git_blob_utf8;
    if(!SHA.test(row.claimed_git_blob_sha1)||blob1(raw)!==row.claimed_git_blob_sha1||
       !SHA256.test(row.claimed_raw_sha256)||digest256(raw)!==row.claimed_raw_sha256)
      bad('record_'+i+'_blob_digest_mismatch');
    let rec;
    try{rec=JSON.parse(raw)}catch{bad('record_'+i+'_json_invalid');continue}
    if(!isObj(rec)||rec.race_code!==code||
        (kind==='clean' ? rec.formal!==false : rec.formal!==undefined&&rec.formal!==false)||
        rec.validated!==false){bad('record_'+i+'_race_or_research_status_invalid');continue}
    const generated=clock(kind==='clean'?rec.generated_at:rec.generated_at_jst);
    const title=clock(rec.source_title_received_jst),cards=clock(rec.source_cards_received_jst);
    const deadline=clock(kind==='clean'?rec.source_deadline_jst:rec.deadline_jst);
    const cutoff=kind==='clean'?clock(rec.cutoff_jst):deadline===null?null:deadline-12*60_000;
    // Date in the race code is JAPAN local date, not UTC date.
    // The source timestamps must be aware +09:00; do not accept an
    // unrelated UTC calendar day simply because it matches the race code.
    if([generated,title,cards,deadline,cutoff].some(x=>x===null)||
       new Date(deadline+9*3600000).toISOString().slice(0,10).replaceAll('-','')!==code.slice(0,8)){
      bad('record_'+i+'_clock_or_race_date_invalid');continue;
    }
    if(kind==='clean'){
      if(rec.status!=='prospective_candidate'||deadline-cutoff!==12*60_000||
         !SHA256.test(rec.source_title_sha256)||!SHA256.test(rec.source_cards_sha256)||
         rec.input_sha256!==digest256(rec.source_title_sha256+':'+rec.source_cards_sha256))
        bad('record_'+i+'_clean_source_contract_invalid');
    }else{
      if(rec.schema!=='CLEAN_FOUR_MODES_PREDEADLINE_V1'||rec.status!=='provisional'||
         !isObj(rec.source_sha256)||!SHA256.test(rec.source_sha256.title)||
         !SHA256.test(rec.source_sha256.race_cards)||!isObj(rec.modes)||
         modes.some(name=>!Object.hasOwn(rec.modes,name)))
        bad('record_'+i+'_four_mode_source_contract_invalid');
    }
    if(title>generated||cards>generated||generated>=cutoff ||
       kind==='four_mode'&&generated>=deadline-20*60_000 ||
       committed!==null&&(committed<=generated||committed>=cutoff))
      bad('record_'+i+'_chronology_invalid');
  }
  if(Array.isArray(input.claimed_added_paths)&&(
      input.claimed_added_paths.length!==paths.length||
      new Set(input.claimed_added_paths).size!==paths.length||
      paths.some(p=>!input.claimed_added_paths.includes(p))))
      bad('claimed_first_add_roster_mismatch');
  return failSafeResult(issues,records.length,kind);
}

// Helper for offline test manifests only. It does NOT fetch or sign a Git blob.
export function computeLocalBlobHashes(raw){
  if(typeof raw!=='string')throw Error('raw_blob_not_string');
  return {git_blob_sha1:blob1(raw),raw_sha256:digest256(raw)};
}
