#!/usr/bin/env bash
# Read-only same-runner diagnostics. Never count as browser E2E success.
set -uo pipefail
host='boat-edge-clean.onrender.com'
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
 echo "RENDER_DIAG_PROBE name=$label curl_exit=$rc $(printf '%s' "$result" | tr '\n' ' ') cors=$cors"
}
# Non-gating check: Render Free serves /robots.txt itself while the instance is idle.
probe_robots() {
 local body result rc klass
 body=$(mktemp) || return 0
 result=$(curl --silent --show-error --connect-timeout 4 --max-time 10 --retry 0 \
  --output "$body" \
  --write-out 'http=%{http_code} ip=%{remote_ip} dns=%{time_namelookup} tcp=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}' \
  'https://boat-edge-clean.onrender.com/robots.txt' 2>&1)
 rc=$?
 klass='unclassified'
 if [[ "$rc" != 0 ]]; then
  klass='no-http-response'
 elif grep -Eiq '^[[:space:]]*Disallow:[[:space:]]*/[[:space:]]*
probe health-head 'https://boat-edge-clean.onrender.com/healthz' HEAD no
probe health-get 'https://boat-edge-clean.onrender.com/healthz' GET no
# Non-gating cold-start discriminator: one long wait, not a replacement for strict 16s checks.
# If only this succeeds, report slow recovery rather than marking browser E2E green.
probe health-longwait 'https://boat-edge-clean.onrender.com/healthz' GET no 120
probe archive-get 'https://boat-edge-clean.onrender.com/api/four-mode-archive?code=202611061006' GET yes
probe racecard-get 'https://boat-edge-clean.onrender.com/api/clean-racecard?hd=20261108&jcd=10&rno=6' GET yes
# Pin both distinct IPv4 edges, if DNS provides them.
while IFS= read -r edge_ip; do
 [[ "$edge_ip" =~ ^[0-9.]+$ ]] || continue
 probe_edge_health "$edge_ip"
done < <(printf '%s\n' "$dns_output" | awk '{print $1}' | sort -u | head -n 2)
echo 'RENDER_DIAG_END never_substitutes_for_live_browser_e2e=true'
 "$body"; then
  klass='possible-free-idle-response'
 elif grep -Fqx 'not found' "$body"; then
  klass='origin-404-body'
 fi
 echo "RENDER_DIAG_ROBOTS curl_exit=$rc class=$klass bytes=$(wc -c < "$body" | tr -d ' ') $(printf '%s' "$result" | tr '\n' ' ')"
 rm -f "$body"
}
# Non-gating per-edge HTTPS check: preserve Host/SNI while pinning each resolved IP.
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
probe_robots
probe health-head 'https://boat-edge-clean.onrender.com/healthz' HEAD no
probe health-get 'https://boat-edge-clean.onrender.com/healthz' GET no
# Non-gating cold-start discriminator: one long wait, not a replacement for strict 16s checks.
# If only this succeeds, report slow recovery rather than marking browser E2E green.
probe health-longwait 'https://boat-edge-clean.onrender.com/healthz' GET no 120
probe archive-get 'https://boat-edge-clean.onrender.com/api/four-mode-archive?code=202611061006' GET yes
probe racecard-get 'https://boat-edge-clean.onrender.com/api/clean-racecard?hd=20261108&jcd=10&rno=6' GET yes
echo 'RENDER_DIAG_END never_substitutes_for_live_browser_e2e=true'
