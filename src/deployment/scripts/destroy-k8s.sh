#!/usr/bin/env bash
# Take the cluster down cleanly: delete the workloads first, so GKE removes the Gateway's load
# balancer (and lets go of the static IP), then destroy the deploy_k8s stack. Destroying the cluster
# with the Gateway still in it can leave load balancer parts behind, holding the IP and still billing.
# deploy_base (the IP, the registry and your chats) is not touched.
#   ./scripts/destroy-k8s.sh          (STACK=dev by default)
set -euo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
stack="${STACK:-dev}"
output() { (cd "$1" && pulumi stack output --stack "${stack}" "$2"); }

cluster="$(output deploy_k8s cluster_name)"
zone="$(output deploy_k8s cluster_location)"
gateway_ip="$(output deploy_base gateway_ip)"
gcloud container clusters get-credentials "${cluster}" --zone "${zone}" --project "${GCP_PROJECT}"
context="gke_${GCP_PROJECT}_${zone}_${cluster}"

# About 6 minutes on GKE: the API pods take up to 150 s to stop, and GKE removes the load balancer's
# network endpoint groups before the namespace can go
kubectl --context "${context}" delete namespace cheese-app --ignore-not-found --wait=true --timeout=900s
echo "Waiting for the load balancer to let go of ${gateway_ip}..."
for _ in $(seq 1 60); do
    rules="$(gcloud compute forwarding-rules list --global --filter="IPAddress=${gateway_ip}" --format="value(name)")"
    [[ -z "${rules}" ]] && break
    sleep 10
done
if [[ -n "${rules}" ]]; then
    echo "The load balancer still holds ${gateway_ip} (${rules}); not destroying the cluster yet." >&2
    exit 1
fi

(cd deploy_k8s && pulumi destroy --stack "${stack}" --yes --non-interactive)
echo "Cluster destroyed."
