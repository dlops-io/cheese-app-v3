#!/bin/bash

set -e

export SECRETS_DIR=$(pwd)/../../../secrets/
export GCP_PROJECT="ac215-project" # CHANGE TO YOUR PROJECT ID
export GOOGLE_APPLICATION_CREDENTIALS="/secrets/ml-workflow.json"
export IMAGE_NAME="cheese-app-vector-db-cli"

# Create the network if we don't have it yet
docker network inspect cheese-app-network >/dev/null 2>&1 || docker network create cheese-app-network

# Build the image based on the Dockerfile
docker build -t "$IMAGE_NAME" -f Dockerfile .

# Start Chroma, which keeps running after this shell closes, and open a shell in the CLI container
docker compose run --rm "$IMAGE_NAME"
