#!/usr/bin/env bash
# Build the production images, copy them into the kind cluster's nodes and start the Cheese App.
#   ./scripts/deploy-kind.sh                  (after ./scripts/create-cluster-kind.sh)
#   RELOAD_BOOKS=1 ./scripts/deploy-kind.sh   load the books into Chroma again
set -euo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
cluster=cheese-app
tag=local
key=/secrets/ml-workflow.json # the same key the API uses in docker
k() { kubectl --context "kind-${cluster}" -n cheese-app "$@"; }

if [[ ! -f "${key}" ]]; then
    echo "${key} is missing: the API needs it for Gemini. Put ml-workflow.json in your secrets folder." >&2
    exit 1
fi

# image <folder> <name>: build it for this laptop and copy it into every node. No registry here.
image() {
    docker build -t "$2:${tag}" "/$1"
    kind load docker-image "$2:${tag}" --name "${cluster}"
}
image api-service cheese-app-api-service
image frontend-react cheese-app-frontend-react
image vector-db cheese-app-vector-db-cli

# Pull the public images onto every node now, so that nothing downloads during class. `kind load`
# can't do these: they are multi-architecture images, and Docker holds only this machine's half.
for node in $(kind get nodes --name "${cluster}"); do
    for public in chromadb/chroma:1.5.9 fsouza/fake-gcs-server:1.56.1; do
        docker exec "${node}" crictl pull "${public}" >/dev/null
    done
done

# What GKE gets from Workload Identity and the project: the key as a Secret, the project as settings
k apply -f k8s/base/namespace.yaml
k create secret generic gcp-key --from-file=key.json="${key}" --dry-run=client -o yaml | k apply -f -
k create configmap gcp-settings --from-literal=GCP_PROJECT="${GCP_PROJECT}" --dry-run=client -o yaml | k apply -f -

redeploy=$(k get deployment api-service -o name 2>/dev/null || true)
k apply -k k8s/kind
if [[ -n "${redeploy}" ]]; then
    k rollout restart deployment/api-service deployment/frontend-react # pick up rebuilt images
fi
k rollout status statefulset/vector-db --timeout=300s
k rollout status deployment/chat-storage --timeout=120s

# Once per cluster: Chroma keeps the books on its disk, and a Job cannot be changed after it is created
if [[ "${RELOAD_BOOKS:-}" == 1 ]] || ! k get job load-vector-db >/dev/null 2>&1; then
    k delete job load-vector-db --ignore-not-found
    k apply -k k8s/kind/load-vector-db
    k wait job/load-vector-db --for=condition=Complete --timeout=600s
fi

# Each API pod downloads the CNN model when it starts, so this can take a minute
for deployment in api-service frontend-react; do
    k rollout status "deployment/${deployment}" --timeout=420s
done

cat <<MSG

Deployed to kind-${cluster}: http://localhost:8090
  Watch:  kubectl get pods,hpa -w
  Load:   ./scripts/load.sh 3000 8
MSG
