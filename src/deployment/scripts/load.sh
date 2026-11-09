#!/usr/bin/env bash
# Keep the API busy: Identify requests, each a cheese photo for the CNN. They never call Gemini, so
# they cost nothing, and the CPU they take is what the autoscaler sees.
#   ./scripts/load.sh 2000 8                               2000 requests, 8 at a time, on kind
#   ./scripts/load.sh 2000 8 http://<your GKE address>     the same on GKE
set -euo pipefail
requests="${1:?How many requests?}"
parallel="${2:-8}"
page="${3:-http://localhost:8090}"
photo=/api-service/news-letters/assets/blue-cheese.jpg
session=00000000-0000-4000-8000-000000000001 # one made-up visitor for all of them

body=$(mktemp)
results=$(mktemp)
trap 'rm -f "${body}" "${results}"' EXIT
printf '{"image": "data:image/jpeg;base64,%s"}' "$(base64 -w0 "${photo}")" >"${body}"

echo "Sending ${requests} Identify requests to ${page}, ${parallel} at a time..."
start=${SECONDS}
seq "${requests}" | xargs -P "${parallel}" -I{} \
    curl -s -o /dev/null -m 60 -w '%{http_code} %{time_total}\n' -X POST "${page}/api/llm-cnn/chats" \
    -H 'Content-Type: application/json' -H "X-Session-ID: ${session}" --data-binary "@${body}" \
    >"${results}" || true # a failed request is counted below, not a reason to stop
seconds=$((SECONDS - start))

ok=$(awk '$1 == 200' "${results}" | wc -l)
failed=$((requests - ok))
p95=$(awk '$1 == 200 { print $2 }' "${results}" | sort -n | awk '{ t[NR] = $1 } END { print NR ? t[int(NR * 0.95 + 0.5)] : "-" }')
echo "${ok} of ${requests} OK in ${seconds} s, 95% within ${p95} s"
if ((failed > 0)); then
    echo "Failed:"
    awk '$1 != 200 { print "  HTTP " $1 }' "${results}" | sort | uniq -c
fi
echo "requests=${requests} ok=${ok} failed=${failed} seconds=${seconds} p95=${p95}"
((failed == 0))
