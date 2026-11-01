#!/bin/bash

echo "Container is running!!!"
echo "Architecture: $(uname -m)"
echo "Python version: $(python --version)"
echo "kubectl $(kubectl version --client -o json | jq -r .clientVersion.gitVersion), pulumi $(pulumi version)"
docker info >/dev/null 2>&1 || echo "WARNING: cannot reach Docker through /var/run/docker.sock"

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

# Run Bash for interactive mode, or the given script
if [[ $# -eq 0 ]]; then
    exec /bin/bash
else
    exec /bin/bash "$@"
fi
