#!/usr/bin/env bash
# Read-only same-runner diagnostics. Never count as browser E2E success.
set -uo pipefail
host='boat-edge-clean.onrender.com'
# Report evidence separately from the workflow's broader browser/test success.
health_http='unverified'
archive_cors='unverified'
robots_before='unverified'
robots_after='unverified'
proxy='no'
if env | grep -Eq '^(HTTPS_PROXY|https_proxy)='; then proxy='yes'; fi
echo "RENDER_DIAG_BEGIN UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ) proxy_configured=$proxy"
dns_output=$(getent ahostsv4 "$host" 2>&1)
dns_rc=$?
echo "RENDER_DIAG_DNS status=$dns_rc addresses=$(printf '%s\n' "$dns_output" | awk '{print $1}' | sort -u | paste -sd, - | cut -c1-300)"
probe() {
 local label="$1" url="$2" method="$3" with_origin="$4" hdr result rc cors
 local max_time="${5:-16}"
 hdr=$(mktemp) || return 0
 local methodflag=''
 if [[ "$method" == HEAD ]]; then methodflag='--head'; fi
 local fmt='http=%{http_code} ip=%{remote_ip} dns=%{time_namelookup} tcp=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}'
 if [[ "$with_origin" == yes ]]; then
  result=$(curl --silent --show-error --location --max-redirs 2 --connect-timeout 5 --max-time "$max_time" --retry 0 --output /dev/null --dump-header "$hdr" --write-out "$fmt" $methodflag --header 'Origin: https://ikst2512-eng.github.io' "$url" 2>&1)
 else
  result=$(curl --silent --show-error --location --max-redirs 2 --connect-timeout 5 --max-time "$max_time" --retry 0 --output /dev/null --dump-header "$hdr" --write-out "$fmt" $methodflag "$url" 2>&1)
 fi
 rc=$?
 cors=$(grep -i '^access-control-allow-origin:' "$hdr" | tail -n 1 | tr -d '\r' | cut -d' ' -f2-)
 rm -f "$hdr"
 if [[ "$label" == health-get ]]; then
  if [[ "$rc" -eq 0 && "$result" == *'http=200 '* ]]; then health_http='pass'; else health_http='fail'; fi
 fi
 if [[ "$label" == archive-get ]]; then
  # Distinguish a real HTTP 200 with a missing/mismatched ACAO header from
  # an unreachable endpoint. Never promote an incorrect CORS header to pass.
  if [[ "$rc" -ne 0 || "$result" != *'http=200 '* ]]; then
   archive_cors='http_not_200'
  elif [[ "$cors" == 'https://ikst2512-eng.github.io' ]]; then
   archive_cors='pass'
  elif [[ -z "$cors" ]]; then
   archive_cors='missing'
  else
   archive_cors='mismatch'
  fi
 fi
 echo "RENDER_DIAG_PROBE name=$label curl_exit=$rc $(printf '%s' "$result" | tr '\n' ' ') cors=$cors"
}
# Render Free serves /robots.txt automatically during idle; the live app returns 404.
# Diagnostic-only: read-only, no readiness override, never counts as E2E success.
probe_robots() {
 local body result rc klass phase="${1:-before}"
 body=$(mktemp) || return 0
 result=$(curl --silent --show-error --connect-timeout 4 --max-time 10 --retry 0 \
  --output "$body" \
  --write-out 'http=%{http_code} ip=%{remote_ip} dns=%{time_namelookup} tcp=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}' \
  'https://boat-edge-clean.onrender.com/robots.txt' 2>&1)
 rc=$?
 klass='unclassified'
 if [[ "$rc" != 0 ]]; then
  klass='no-http-response'
 elif grep -Eiq '^[[:space:]]*Disallow:[[:space:]]*/[[:space:]]*$' "$body"; then
  klass='possible-free-idle-response'
 elif grep -Fqx 'not found' "$body"; then
  klass='origin-404-body'
 fi
 case "$phase" in
  before) robots_before="$klass" ;;
  after_wake_attempt) robots_after="$klass" ;;
 esac
 echo "RENDER_DIAG_ROBOTS phase=$phase curl_exit=$rc class=$klass bytes=$(wc -c < "$body" | tr -d ' ') $(printf '%s' "$result" | tr '\n' ' ')"
 rm -f "$body"
}
# Pin each known IPv4 Render edge independently while preserving HTTPS Host/SNI.
probe_edge_health() {
 local ip="$1" result rc
 result=$(curl --silent --show-error --connect-timeout 4 --max-time 10 --retry 0 \
  --noproxy "$host" --resolve "${host}:443:${ip}" \
  --output /dev/null \
  --write-out 'http=%{http_code} ip=%{remote_ip} dns=%{time_namelookup} tcp=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}' \
  "https://${host}/healthz" 2>&1)
 rc=$?
 echo "RENDER_DIAG_EDGE_HEALTH target_ip=$ip curl_exit=$rc $(printf '%s' "$result" | tr '\n' ' ')"
}

probe pages-control 'https://ikst2512-eng.github.io/boat-edge-clean/' GET no
probe_robots before
probe health-head 'https://boat-edge-clean.onrender.com/healthz' HEAD no
probe health-get 'https://boat-edge-clean.onrender.com/healthz' GET no
# Non-gating cold-start discriminator: one long wait, not a replacement for strict 16s checks.
# If only this succeeds, report slow recovery rather than marking browser E2E green.
probe health-longwait 'https://boat-edge-clean.onrender.com/healthz' GET no 120
probe archive-get 'https://boat-edge-clean.onrender.com/api/four-mode-archive?code=202611061006' GET yes
probe racecard-get 'https://boat-edge-clean.onrender.com/api/clean-racecard?hd=20261108&jcd=10&rno=6' GET yes
# Non-gating IPv4 edge probes. Do not alter production instance or service settings.
while IFS= read -r edge_ip; do
 [[ "$edge_ip" =~ ^[0-9.]+$ ]] || continue
 probe_edge_health "$edge_ip"
done < <(printf '%s\n' "$dns_output" | awk '{print $1}' | sort -u | head -n 2)
# Observe idle status AFTER all /healthz and racecard wake requests.
# If this remains edge-generated, the origin is still not serving traffic.
probe_robots after_wake_attempt
echo "RENDER_DIAG_RELEASE_GATES health_http=$health_http live_archive_cors=$archive_cors robots_before=$robots_before robots_after=$robots_after live_exhibition=unassessed no_deploy_cold_start=unassessed"
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
 {
  echo '### Render HTTP diagnostics — not a production release approval'
  echo "- /healthz transport: $health_http"
  echo "- Live Pages→Render archive CORS: $archive_cors"
  echo "- /robots.txt before/after: $robots_before / $robots_after"
  echo '- Live exhibition six-boat verification: not assessed by this probe'
  echo '- No-deploy 15-minute idle→wake recovery: not assessed by this probe'
  echo '- A green browser workflow can include PR-only simulated CORS and archival test cases.'
 } >> "$GITHUB_STEP_SUMMARY"
fi
echo 'RENDER_DIAG_END never_substitutes_for_live_browser_e2e=true'
