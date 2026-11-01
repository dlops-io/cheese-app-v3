#!/bin/bash
# The manual deployment as a script: the VM runs this as root at every boot. Compare it with the
# commands you typed by hand. deploy_vm/__main__.py puts these settings in front of it:
#   GCP_PROJECT, REGISTRY_HOST, API_IMAGE, FRONTEND_IMAGE, VECTOR_DB_CLI_IMAGE, CHAT_BUCKET
set -euo pipefail
export HOME=/root
data=/var/lib/cheese-app

# Docker, the first time
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh

# Pull from Artifact Registry as the VM's service account: no key file on the VM
gcloud auth configure-docker "${REGISTRY_HOST}" --quiet

mkdir -p "${data}/chromadb" "${data}/persistent"
chmod 0777 "${data}/persistent" # the API runs as a non-root user

docker network inspect cheese-app-network >/dev/null 2>&1 || docker network create cheese-app-network

# Start from clean containers. The data is in ${data}, and survives this.
docker rm -f cheese-app-frontend-react cheese-app-api-service cheese-app-vector-db 2>/dev/null || true

docker run -d --name cheese-app-vector-db --network cheese-app-network \
    -e ANONYMIZED_TELEMETRY=FALSE \
    -v "${data}/chromadb":/data \
    --restart always \
    chromadb/chroma:1.5.9

# Once per VM: Chroma keeps the books on the disk. It may still be starting, so try a few times.
if [[ ! -f "${data}/books-loaded" ]]; then
    for _ in 1 2 3 4 5; do
        if docker run --rm --network cheese-app-network \
            -e GCP_PROJECT="${GCP_PROJECT}" \
            -e CHROMADB_HOST=cheese-app-vector-db \
            -e CHROMADB_PORT=8000 \
            "${VECTOR_DB_CLI_IMAGE}" \
            cli.py --download --load --chunk_type recursive-split; then
            touch "${data}/books-loaded"
            break
        fi
        sleep 5
    done
fi

# The API first: nginx in the frontend looks it up when it starts
docker run -d --name cheese-app-api-service --network cheese-app-network \
    -v "${data}/persistent":/persistent \
    -e GCP_PROJECT="${GCP_PROJECT}" \
    -e CHAT_BUCKET="${CHAT_BUCKET}" \
    --restart always \
    "${API_IMAGE}"

docker run -d --name cheese-app-frontend-react --network cheese-app-network \
    -p 80:80 \
    --restart always \
    "${FRONTEND_IMAGE}"

echo "Cheese App containers started"
