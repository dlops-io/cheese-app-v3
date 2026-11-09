#!/usr/bin/env bash
# Rehearse the local Kubernetes tutorial before class: delete the kind cluster, build a new one, deploy
# the Cheese App and check each thing the tutorial shows. Prints the numbers for the slides and exits
# non-zero if a check failed. It asks Gemini one question; SKIP_GEMINI=1 leaves that out.
#   ./scripts/verify-kind.sh
set -uo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")/.." || exit 1
page=http://localhost:8090
session=00000000-0000-4000-8000-000000000002
load_requests=${LOAD_REQUESTS:-3000}
load_parallel=${LOAD_PARALLEL:-8}
books=14356 # chunks in recursive-split-collection
passed=0
failed=0

k() { kubectl --context kind-cheese-app -n cheese-app "$@"; }
step() { printf '\n=== %s\n' "$*"; }

check() { # check "what should be true" <command>
    local claim=$1
    shift
    if "$@" >/dev/null 2>&1; then
        passed=$((passed + 1))
        echo "PASS  ${claim}"
    else
        failed=$((failed + 1))
        echo "FAIL  ${claim}"
    fi
}

wait_until() { # wait_until <seconds> <command>
    local deadline=$((SECONDS + $1))
    shift
    until "$@" >/dev/null 2>&1; do
        ((SECONDS < deadline)) || return 1
        sleep 1
    done
}

api_pods() {
    local count
    count=$(k get deployment api-service -o jsonpath='{.status.replicas}')
    echo "${count:-0}"
}
api_pod_names() { k get pods -l app=api-service -o jsonpath='{.items[*].metadata.name}'; }
api_pods_are() { [[ "$(api_pods)" -eq $1 ]] && [[ "$(k get pods -l app=api-service --no-headers | wc -l)" -eq $1 ]]; }
cpu() { k get hpa api-service -o jsonpath='{.status.currentMetrics[0].resource.current.averageUtilization}'; }
cpu_has_a_reading() { [[ -n "$(cpu)" ]]; }
restarts() {
    k get pods -o jsonpath='{.items[*].status.containerStatuses[*].restartCount}' |
        tr ' ' '\n' | awk '{ sum += $1 } END { print sum + 0 }'
}

chunks() {
    k exec deploy/api-service -- python -c "import chromadb
print(chromadb.HttpClient(host='vector-db', port=8000).get_collection('recursive-split-collection').count())"
}
has_all_books() { [[ "$(chunks)" -eq ${books} ]]; }

post() { # post <mode> <json>: a new chat, as the page sends it
    curl -fsS -m 120 -X POST "${page}/api/$1/chats" -H 'Content-Type: application/json' \
        -H "X-Session-ID: ${session}" -d "$2"
}
photo() { printf '{"image": "data:image/jpeg;base64,%s"}' "$(base64 -w0 /api-service/news-letters/assets/blue-cheese.jpg)"; }

pod_sees_chat() { # pod_sees_chat <pod>: the pod reads the chat from storage itself, not through a peer
    k exec "$1" -- python -c "import sys
from api.utils.chat_utils import ChatHistoryManager
sys.exit(0 if ChatHistoryManager('llm-cnn').get_chat('${chat_id}', '${session}') else 1)"
}
every_pod_sees_chat() {
    local pod
    for pod in $(api_pod_names); do
        pod_sees_chat "${pod}" || return 1
    done
}

# Send load in the background and sample the API once a second until it is done. Sets first_s (first
# new pod), peak, load_ok and load_line.
load_and_watch() { # load_and_watch <requests> [command to run once the load has started]
    local out start pods
    out=$(mktemp)
    ./scripts/load.sh "$1" "${load_parallel}" "${page}" >"${out}" 2>&1 &
    local loader=$!
    start=${SECONDS} first_s='' peak=$(api_pods)
    local floor=${peak}
    sleep 5
    [[ $# -gt 1 ]] && "${@:2}"
    while kill -0 "${loader}" 2>/dev/null; do
        pods=$(api_pods)
        ((pods > peak)) && peak=${pods}
        [[ -z "${first_s}" ]] && ((pods > floor)) && first_s=$((SECONDS - start))
        sleep 1
    done
    wait "${loader}"
    load_ok=$?
    load_line=$(grep ' OK in ' "${out}")
    rm -f "${out}"
}

step "Set up, before class"
setup_from=${SECONDS}
./scripts/delete-cluster-kind.sh
./scripts/create-cluster-kind.sh || exit 1
./scripts/deploy-kind.sh || exit 1
setup_s=$((SECONDS - setup_from))
check "The page answers" curl -fsS -o /dev/null "${page}/"
check "The API answers through the page, version 3.0.0" \
    bash -c "curl -fsS ${page}/api/status | jq -e '.version == \"3.0.0\"'"
check "Newsletters load through the API" bash -c "curl -fsS ${page}/api/newsletters | jq -e 'length > 0'"
check "Chroma has all ${books} chunks of the books" has_all_books

step "Two API pods, and an autoscaler watching them"
check "Two API pods" api_pods_are 2
reading_from=${SECONDS}
wait_until 120 cpu_has_a_reading
check "The HPA has a CPU reading after $((SECONDS - reading_from)) s ($(cpu)%)" cpu_has_a_reading

step "Chats live outside the pods"
chat_id=$(post llm-cnn "$(photo)" | jq -r '.chat_id')
check "Identify names the cheese in a photo (chat ${chat_id})" [ "${chat_id:-null}" != null ]
check "Every API pod reads that chat from the shared storage" every_pod_sees_chat
if [[ "${SKIP_GEMINI:-}" != 1 ]]; then
    answer=$(post llm '{"content": "In one sentence, what is Brie?"}' | jq -r '.messages[-1].content')
    check "Gemini answers through the key Secret: ${answer:0:60}..." [ "${#answer}" -gt 20 ]
fi

step "Load: the autoscaler adds pods"
load_and_watch "${load_requests}"
load_s=${SECONDS}
scale_line="first new pod ${first_s:--} s, peak ${peak} pods, ${load_line}" # the next load overwrites these
check "The first new pod arrived within a minute (${first_s:-never} s)" [ "${first_s:-99}" -le 60 ]
check "It reached 6 pods (${peak})" [ "${peak}" -eq 6 ]
check "No request failed: ${load_line}" [ "${load_ok}" -eq 0 ]
wait_until 300 api_pods_are 2
settled_s=$((SECONDS - load_s))
check "Back to 2 pods ${settled_s} s after the load stopped" api_pods_are 2

step "A rolling update while people use it"
rollout() { k rollout restart deployment/api-service >/dev/null; }
none_left_of() { # none_left_of <pods>: none of these API pods is still running
    local pod
    for pod in $1; do
        [[ " $(api_pod_names) " == *" ${pod} "* ]] && return 1
    done
    return 0
}
before=$(api_pod_names)
rolled_from=${SECONDS}
load_and_watch $((load_requests / 3)) rollout
k rollout status deployment/api-service --timeout=300s >/dev/null
check "Every API pod was replaced, in $((SECONDS - rolled_from)) s" none_left_of "${before}"
check "No request failed during the update: ${load_line}" [ "${load_ok}" -eq 0 ]
check "The new pods still see the chat from before" every_pod_sees_chat

step "Chroma restarts with its books"
k delete pod vector-db-0 >/dev/null
chroma_from=${SECONDS}
wait_until 30 bash -c "! kubectl --context kind-cheese-app -n cheese-app get pod vector-db-0 -o jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}' | grep -q True"
k rollout status statefulset/vector-db --timeout=120s >/dev/null
check "Chroma is back in $((SECONDS - chroma_from)) s with all ${books} chunks" has_all_books

step "At the end"
check "Nothing restarted" [ "$(restarts)" -eq 0 ]

printf '\nSetup %s s. Load: %s. Back to 2 pods %s s after it stopped.\n' "${setup_s}" "${scale_line}" "${settled_s}"
printf '%s passed, %s failed\n' "${passed}" "${failed}"
((failed == 0))
