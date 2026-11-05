#!/usr/bin/env bash
# Delete the local cluster and free the laptop's CPU and memory. Nothing on GCP is touched.
#   ./scripts/delete-cluster-kind.sh
set -euo pipefail
kind delete cluster --name cheese-app
