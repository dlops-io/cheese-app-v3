#!/bin/bash

set -e

export IMAGE_NAME="cheese-app-api-service"
export BASE_DIR=$(pwd)
export SECRETS_DIR=$(pwd)/../../../secrets/
export PERSISTENT_DIR=$(pwd)/../../../persistent-folder/
export GCP_PROJECT="ac215-project" # CHANGE TO YOUR PROJECT ID
export CHROMADB_HOST="cheese-app-vector-db"
export CHROMADB_PORT=8000

# Create the network if we don't have it yet
docker network inspect cheese-app-network >/dev/null 2>&1 || docker network create cheese-app-network

if docker ps --format "{{.Names}}" | grep -qx "${IMAGE_NAME}"; then
    echo "Container '${IMAGE_NAME}' is already running. Shelling into it..."
    docker exec -it "$IMAGE_NAME" /bin/bash
else
    echo "Building ${IMAGE_NAME} (Dockerfile.dev)..."
    docker build -t "$IMAGE_NAME" -f Dockerfile.dev .

    # Run the container
    docker run --rm --name "$IMAGE_NAME" -ti \
        -v "$BASE_DIR":/app \
        -v "$SECRETS_DIR":/secrets:ro \
        -v "$PERSISTENT_DIR":/persistent \
        -p 9000:9000 \
        -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/ml-workflow.json \
        -e GCP_PROJECT="$GCP_PROJECT" \
        -e CHROMADB_HOST="$CHROMADB_HOST" \
        -e CHROMADB_PORT="$CHROMADB_PORT" \
        --network cheese-app-network \
        "$IMAGE_NAME"
fi
