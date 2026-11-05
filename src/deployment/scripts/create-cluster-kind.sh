#!/usr/bin/env bash
# Create the local cluster and everything autoscaling needs.
#   ./scripts/create-cluster-kind.sh
set -euo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
cluster=cheese-app
context="kind-${cluster}"
metrics_server=v0.9.1

kind create cluster --name "${cluster}" --config kind.yaml --wait 180s

# metrics-server measures pod CPU for the autoscaler. kind's kubelets use self-signed certificates,
# which is what --kubelet-insecure-tls is for; GKE has its own and does not need it.
kubectl --context "${context}" apply -f "https://github.com/kubernetes-sigs/metrics-server/releases/download/${metrics_server}/components.yaml"
kubectl --context "${context}" -n kube-system patch deployment metrics-server --type=json \
    -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl --context "${context}" -n kube-system rollout status deployment/metrics-server --timeout=180s

# Every kubectl command in the tutorial works on this cluster and namespace
kubectl --context "${context}" apply -f k8s/base/namespace.yaml
kubectl config use-context "${context}"
kubectl config set-context --current --namespace=cheese-app

kubectl get nodes
