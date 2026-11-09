#!/bin/bash

set -e

export IMAGE_NAME="cheese-app-frontend-react"

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
        -v "$(pwd)":/app \
        -v "${IMAGE_NAME}-node_modules:/app/node_modules" \
        -p 3000:5173 \
        --network cheese-app-network \
        "$IMAGE_NAME"
fi
