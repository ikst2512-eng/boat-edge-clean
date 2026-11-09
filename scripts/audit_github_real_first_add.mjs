#!/usr/bin/env node
// Read-only public GitHub REST commit/blob/parent/main verification.
// No secrets, dispatch, repository writes or Cloudflare actions.
// Usage: node scripts/audit_github_real_first_add.mjs clean 202611090203 <commit sha>
import {verifyRealGithubFirstAdd} from '../cloudflare/remote_github_first_add_audit.mjs';

const [publisher,raceCode,commitSha]=process.argv.slice(2);
if(process.argv.length!==5) {
  console.error('usage: node scripts/audit_github_real_first_add.mjs <clean|four_mode> <12-digit-race-code> <40-char-git-commit>');
  process.exitCode=2;
}else{
  try {
    const result=await verifyRealGithubFirstAdd({publisher,raceCode,commitSha});
    console.log(JSON.stringify(result,null,2));
  } catch(e) {
    const allowed=new Set([
      'invalid_remote_github_sample_request','github_commit_metadata_invalid',
      'github_commit_path_not_first_add','github_commit_clock_missing',
      'github_contents_identity_mismatch','github_blob_payload_invalid',
      'github_blob_base64_invalid','github_blob_size_invalid',
      'github_blob_size_mismatch','github_blob_sha_mismatch',
      'github_blob_bytes_mismatch','github_parent_file_absence_unproven',
      'github_commit_main_ancestry_unproven','original_archive_json_invalid',
      'original_archive_identity_invalid','archive_clock_order_invalid',
      'clean_archive_source_contract_invalid','four_mode_archive_source_contract_invalid'
    ]);
    console.error('READONLY_GITHUB_FIRST_ADD_REJECTED='+
      (e instanceof Error&&allowed.has(e.message)?e.message:'api_or_network_error'));
    process.exitCode=1;
  }
}
