#!/usr/bin/env node
// OFFLINE and READ-ONLY. Consistency of a manually assembled GitHub evidence
// manifest is not proof of GitHub remote first-seen, source authenticity,
// forecast publication, or T-12 eligibility. No credentials or network.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {auditLocalFirstAddEvidence} from '../cloudflare/local_first_add_evidence_lab.mjs';

if(process.argv.length!==3){
  console.error('usage: node scripts/audit_cloudflare_first_add_manifest.mjs <manifest.json>');
  process.exitCode=2;
}else{
  try{
    const raw=readFileSync(process.argv[2]);
    if(raw.length>16_000_000)throw Error('large_input');
    const manifest=JSON.parse(raw.toString('utf8'));
    const input_sha256=createHash('sha256').update(raw).digest('hex');
    const result=auditLocalFirstAddEvidence(manifest);
    console.log(JSON.stringify({...result,input_sha256},null,2));
    if(!result.local_content_consistency_pass)process.exitCode=1;
  }catch{
    // Do not echo operator input bytes, metadata, paths, tokens or exception
    // details: they may contain sensitive material.
    console.error('FIRST_ADD_MANIFEST_REJECTED=parse_or_io_error');
    process.exitCode=2;
  }
}
