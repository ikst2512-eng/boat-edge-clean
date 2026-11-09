// RESEARCH-ONLY read-only Github REST first-add sample verifier.
// NOT imported by Cloudflare Workers, never dispatches, changes Git data,
// or authenticates GitHub server FIRST receipt / official pre-T-12 evidence.
// CLI accepts explicit known native commit, race code and publisher only.
import {createHash} from 'node:crypto';

export const REMOTE_GITHUB_SCHEMA='BOAT_EDGE_REAL_GITHUB_FIRST_ADD_SAMPLE_V1';
const REPO='ikst2512-eng/boat-edge-clean';
const API='https://api.github.com/repos/'+REPO;
const SHA=/^[a-f0-9]{40}$/;
const CODE=/^20[0-9]{10}$/;
const PATHS={clean:'prospective_predictions/',four_mode:'four_mode_forecasts/'};
const ACTUAL_WORKFLOW={clean:'clean-prospective.yml',four_mode:'four-mode-prospective-capture.yml'};
const isObj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
function checkCode(code){
  if(typeof code!=='string'||!CODE.test(code))return false;
  const venue=Number(code.slice(8,10)),race=Number(code.slice(10,12));
  const day=code.slice(0,8);
  const parsed=Date.UTC(Number(day.slice(0,4)),Number(day.slice(4,6))-1,Number(day.slice(6,8)));
  return venue>=1&&venue<=24&&race>=1&&race<=12&&
    Number.isFinite(parsed)&&new Date(parsed).toISOString().slice(0,10).replaceAll('-','')===day;
}
function sha1GitBlob(buf){
  return createHash('sha1').update(Buffer.from('blob '+buf.length+'\0')).update(buf).digest('hex');
}
function sha256(buf){return createHash('sha256').update(buf).digest('hex')}
function utc(t){if(typeof t!=='string')return NaN;return Date.parse(t)}
function local(t){
  return typeof t==='string'&&
    /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?\+09:00$/.test(t)
    ?Date.parse(t):NaN;
}
async function get(fetcher,url){
  // Keep the accessor closed to GitHub's exact known public API origin.
  if(!url.startsWith(API+'/'))throw Error('unauthorized_github_api_url');
  const r=await fetcher(url,{method:'GET',headers:{
    Accept:'application/vnd.github+json',
    'X-GitHub-Api-Version':'2022-11-28',
    'User-Agent':'BOAT-EDGE-CLEAN-READONLY-FIRST-ADD-AUDIT'
  }});
  if(!r||r.status!==200)throw Error('github_read_http_'+(r?.status??'missing'));
  return r.json();
}
function bytesFromBase64(data,max){
  if(!isObj(data)||data.encoding!=='base64'||typeof data.content!=='string')throw Error('github_blob_payload_invalid');
  const compact=data.content.replace(/\s+/g,'');
  if(compact.length>Math.ceil(max/3)*4+8||!/^[A-Za-z0-9+/]*={0,2}$/.test(compact))
    throw Error('github_blob_base64_invalid');
  const buf=Buffer.from(compact,'base64');
  if(!buf.length||buf.length>max||Buffer.from(buf.toString('base64'),'base64').compare(buf)!==0)
    throw Error('github_blob_size_invalid');
  if(typeof data.size==='number'&&data.size!==buf.length)throw Error('github_blob_size_mismatch');
  return buf;
}
function actualRecord(kind,code,buf,commitTime){
  let rec;try{rec=JSON.parse(buf.toString('utf8'))}catch{throw Error('original_archive_json_invalid')}
  if(!isObj(rec)||rec.race_code!==code||rec.validated!==false||
      (rec.formal!==undefined&&rec.formal!==false))throw Error('original_archive_identity_invalid');
  const title=local(rec.source_title_received_jst);
  const cards=local(rec.source_cards_received_jst);
  const generated=local(kind==='clean'?rec.generated_at:rec.generated_at_jst);
  const deadline=local(kind==='clean'?rec.source_deadline_jst:rec.deadline_jst);
  const cutoff=kind==='clean'?local(rec.cutoff_jst):deadline-12*60000;
  if(![title,cards,generated,deadline,cutoff].every(Number.isFinite)||
      new Date(deadline+9*3600000).toISOString().slice(0,10).replaceAll('-','')!==code.slice(0,8)||
      !(title<=generated&&cards<=generated&&generated<commitTime&&commitTime<cutoff))throw Error('archive_clock_order_invalid');
  if(kind==='clean'){
    if(rec.status!=='prospective_candidate'||rec.formal!==false||
       deadline-cutoff!==12*60000||!/^[a-f0-9]{64}$/.test(rec.source_title_sha256)||
       !/^[a-f0-9]{64}$/.test(rec.source_cards_sha256)||
       sha256(Buffer.from(rec.source_title_sha256+':'+rec.source_cards_sha256))!==rec.input_sha256)
      throw Error('clean_archive_source_contract_invalid');
  }else{
    if(rec.status!=='provisional'||rec.schema!=='CLEAN_FOUR_MODES_PREDEADLINE_V1'||
       !isObj(rec.source_sha256)||!/^[a-f0-9]{64}$/.test(rec.source_sha256.title)||
       !/^[a-f0-9]{64}$/.test(rec.source_sha256.race_cards)||
       !isObj(rec.modes)||['hit','balance','hole','narrow'].some(k=>!Object.hasOwn(rec.modes,k))||
       generated>=deadline-20*60000)throw Error('four_mode_archive_source_contract_invalid');
  }
  return {
    code,deadline_jst:new Date(deadline).toISOString(),
    generated_at_jst:kind==='clean'?rec.generated_at:rec.generated_at_jst,
    source_title_received_jst:rec.source_title_received_jst,
    source_cards_received_jst:rec.source_cards_received_jst,
    t_minus_12_jst:new Date(cutoff+9*3600000).toISOString().replace('Z','+09:00'),
    source_title_sha256:kind==='clean'?rec.source_title_sha256:rec.source_sha256.title,
    source_cards_sha256:kind==='clean'?rec.source_cards_sha256:rec.source_sha256.race_cards,
    research_only:true,
  };
}
// Input is intentionally limited: a known commit SHA, a known native workflow
// and an exact race code. The metadata comes from freshly fetched GitHub URLs;
// the caller cannot supply a self-serving "added" manifest.
export async function verifyRealGithubFirstAdd({publisher,raceCode,commitSha,fetcher=fetch}){
  if(!Object.hasOwn(PATHS,publisher)||!checkCode(raceCode)||!SHA.test(commitSha)||
     typeof fetcher!=='function')throw Error('invalid_remote_github_sample_request');
  const path=PATHS[publisher]+raceCode+'.json';
  const enc=path.split('/').map(encodeURIComponent).join('/');
  const commit=await get(fetcher,API+'/commits/'+commitSha);
  if(!isObj(commit)||commit.sha!==commitSha||!Array.isArray(commit.parents)||commit.parents.length!==1||
     !SHA.test(commit.parents[0]?.sha)||!Array.isArray(commit.files))
    throw Error('github_commit_metadata_invalid');
  const parent=commit.parents[0].sha;
  const changed=commit.files.filter(row=>row.filename===path);
  if(changed.length!==1||changed[0].status!=='added'||!SHA.test(changed[0].sha))
    throw Error('github_commit_path_not_first_add');
  const gitBlobSha=changed[0].sha;
  const committer=utc(commit.commit?.committer?.date);
  if(!Number.isFinite(committer))throw Error('github_commit_clock_missing');
  const content=await get(fetcher,API+'/contents/'+enc+'?ref='+commitSha);
  if(content.sha!==gitBlobSha||content.path!==path)throw Error('github_contents_identity_mismatch');
  const a=bytesFromBase64(content,65536);
  const blob=await get(fetcher,API+'/git/blobs/'+gitBlobSha);
  if(blob.sha!==gitBlobSha)throw Error('github_blob_sha_mismatch');
  const b=bytesFromBase64(blob,65536);
  if(!a.equals(b)||sha1GitBlob(a)!==gitBlobSha)
    throw Error('github_blob_bytes_mismatch');
  // Absence in the immediate PARENT is supported by Github 404. Any other
  // HTTP failure (401/403/429/500/503) is ambiguous and fails closed.
  const response=await fetcher(API+'/contents/'+enc+'?ref='+parent,{
    method:'GET',headers:{Accept:'application/vnd.github+json',
      'X-GitHub-Api-Version':'2022-11-28',
      'User-Agent':'BOAT-EDGE-CLEAN-READONLY-FIRST-ADD-AUDIT'}});
  if(!response||response.status!==404)throw Error('github_parent_file_absence_unproven');
  const comp=await get(fetcher,API+'/compare/'+commitSha+'...main');
  if(!isObj(comp)||!['ahead','identical'].includes(comp.status)||
     comp.behind_by!==0||comp.merge_base_commit?.sha!==commitSha)
    throw Error('github_commit_main_ancestry_unproven');
  const record=actualRecord(publisher,raceCode,a,committer);
  return {
    schema:REMOTE_GITHUB_SCHEMA,repository:REPO,publisher,race_code:raceCode,
    native_workflow_expected:ACTUAL_WORKFLOW[publisher],
    git_commit_sha:commitSha, git_parent_sha:parent, git_blob_sha1:gitBlobSha,
    exact_original_sha256:sha256(a),original_byte_length:a.length,
    commit_committer_utc:commit.commit.committer.date,
    source_blob_commit_consistency_pass:true, git_parent_addition_checked:true,
    current_main_ancestry_checked:true, record,
    // Github archive first-add != first time a Github HTTP server accepted it.
    github_remote_first_seen_timestamp_proven:false,
    native_run_id_independently_proven:false,
    cloudflare_rescue_dispatch_proven:false,
    official_beforeinfo_six_boats_proven:false,
    odds_120_combinations_proven:false,
    official_t_minus_12_proven:false,
    formal_recovery_proven:false,
  };
}
