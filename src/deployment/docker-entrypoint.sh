#!/bin/bash

echo "Container is running!!!"
echo "Architecture: $(uname -m)"
echo "Python version: $(python --version)"
echo "kubectl $(kubectl version --client -o json | jq -r .clientVersion.gitVersion), pulumi $(pulumi version), $(kind version)"
docker info >/dev/null 2>&1 || echo "WARNING: cannot reach Docker through /var/run/docker.sock"

# Both clusters' credentials (kind and GKE) stay in the ignored .local/, so they outlive this container
mkdir -p /app/.local
export KUBECONFIG=/app/.local/kubeconfig

# GCP: only with the deployment key. Without it, the local cluster still works.
if [[ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]]; then
    # Authenticate gcloud using service account
    gcloud auth activate-service-account --key-file "$GOOGLE_APPLICATION_CREDENTIALS"
    gcloud config set project "$GCP_PROJECT"
    # login to artifact-registry
    gcloud auth configure-docker "$GCP_REGION-docker.pkg.dev" --quiet
    # Check if the bucket exists
    if ! gcloud storage buckets describe "$PULUMI_BUCKET" >/dev/null 2>&1; then
        echo "Bucket does not exist. Creating..."
        gcloud storage buckets create "$PULUMI_BUCKET" --project "$GCP_PROJECT" \
            --location "$GCP_REGION" --uniform-bucket-level-access
    else
        echo "Bucket already exists. Skipping creation."
    fi
    echo "Logging into Pulumi using GCS bucket: $PULUMI_BUCKET"
    pulumi login "$PULUMI_BUCKET"
else
    echo "No $GOOGLE_APPLICATION_CREDENTIALS: skipping GCP and Pulumi. The local cluster still works."
fi

# Run Bash for interactive mode, or the given script
if [[ $# -eq 0 ]]; then
    echo -en "\033[92m
On your laptop (kind):
    ./scripts/create-cluster-kind.sh    a 3-node cluster with metrics-server
    ./scripts/deploy-kind.sh            build the images, load them and start the app: http://localhost:8090
    ./scripts/load.sh 3000 8            3000 Identify requests, 8 at a time
    ./scripts/verify-kind.sh            rehearse the whole tutorial on a new cluster, about 12 minutes
    ./scripts/delete-cluster-kind.sh    delete the cluster
On GCP: deploy_base, deploy_images, then deploy_vm, or deploy_k8s and ./scripts/deploy-k8s.sh
\033[0m
"
    exec /bin/bash
else
    exec /bin/bash "$@"
fi
