#!/bin/bash
# shellcheck disable=SC2155  # export VAR=$(pwd) is this script's style

# Define some environment variables
export IMAGE_NAME="cheese-app-deployment"
export BASE_DIR=$(pwd)
export SECRETS_DIR=$(pwd)/../../../secrets/
export GCP_PROJECT="ac215-project" # Change to your GCP Project
export GCP_REGION="us-central1"
export GCP_ZONE="us-central1-a"
export GOOGLE_APPLICATION_CREDENTIALS=/secrets/deployment.json
export PULUMI_BUCKET="gs://$GCP_PROJECT-pulumi-state-bucket"

# Create local Pulumi plugins and Docker config directories if they don't exist
# (a folder, not a single config.json: docker login and gcloud replace that file by renaming over it)
mkdir -p "$BASE_DIR/pulumi-plugins" "$BASE_DIR/docker-config"

# Check if container is already running
if docker ps --format "table {{.Names}}" | grep -q "^${IMAGE_NAME}$"; then
    echo "Container '${IMAGE_NAME}' is already running. Shelling into existing container..."
    docker exec -it $IMAGE_NAME /bin/bash ./docker-entrypoint.sh
else
    echo "Container '${IMAGE_NAME}' is not running. Building and starting new container..."

    # Build the image based on the Dockerfile, for this machine's architecture (no emulation)
    docker build -t $IMAGE_NAME -f Dockerfile .

    # Run the container
    # --network host: kind's kubeconfig points at 127.0.0.1 on the Docker host
    # The Docker socket: kind's nodes and the image builds run on the laptop's Docker
    docker run --rm --name $IMAGE_NAME -ti \
    --network host \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$BASE_DIR":/app \
    -v "$SECRETS_DIR":/secrets:ro \
    -v "$(pwd)/docker-config":/root/.docker \
    -v "$(pwd)/pulumi-plugins":/root/.pulumi/plugins \
    -v "$BASE_DIR/../api-service":/api-service \
    -v "$BASE_DIR/../frontend-react":/frontend-react \
    -v "$BASE_DIR/../vector-db":/vector-db \
    -e GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS \
    -e GCP_PROJECT=$GCP_PROJECT \
    -e GCP_REGION=$GCP_REGION \
    -e GCP_ZONE=$GCP_ZONE \
    -e PULUMI_BUCKET=$PULUMI_BUCKET \
    $IMAGE_NAME
fi
