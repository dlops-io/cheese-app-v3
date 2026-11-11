#!/usr/bin/env bash
# Set up the Cheese App on a new VM, from this repo: Docker, the images, the books and the containers.
# On the VM, from the cheese-app-v3 folder:
#   ./src/deployment/vm/setup-vm.sh
# After `git pull`, run it again: it rebuilds what changed and restarts those containers.
set -euo pipefail

# Docker needs root; ask for it once, here
if [[ ${EUID} -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi
cd "$(dirname -- "${BASH_SOURCE[0]}")"

# The data lives outside the repo, so it survives a new clone
export DATA_DIR=/var/lib/cheese-app
# The VM knows its project and address: ask its metadata server, so there is nothing to type
metadata() { curl -fs -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/$1"; }
GCP_PROJECT="$(metadata project/project-id)"
export GCP_PROJECT
address="$(metadata instance/network-interfaces/0/access-configs/0/external-ip || true)"
# docker compose reads .env by itself, so `sudo docker compose ps` and `logs` work here later too
printf 'DATA_DIR=%s\nGCP_PROJECT=%s\n' "${DATA_DIR}" "${GCP_PROJECT}" >.env
started=${SECONDS}

echo "== 1/5 Docker"
if ! command -v docker >/dev/null; then
    curl -fsSL https://get.docker.com | sh
fi
docker --version

echo "== 2/5 Folders for the data, in ${DATA_DIR}"
mkdir -p "${DATA_DIR}/chromadb" "${DATA_DIR}/persistent"
chmod 0777 "${DATA_DIR}/persistent" # the API runs as a non-root user

echo "== 3/5 Build the images from this repo (several minutes the first time)"
docker compose --profile books build

echo "== 4/5 Chroma, and the books (once per VM)"
docker compose up -d vector-db
if [[ ! -f "${DATA_DIR}/books-loaded" ]]; then
    for attempt in 1 2 3 4 5; do # Chroma may still be starting
        if docker compose run --rm load-books; then
            touch "${DATA_DIR}/books-loaded"
            break
        fi
        echo "Loading the books failed (attempt ${attempt}); trying again in 5 s"
        sleep 5
    done
    [[ -f "${DATA_DIR}/books-loaded" ]] || { echo "Could not load the books" >&2; exit 1; }
fi

echo "== 5/5 The API and the frontend"
docker compose up -d --wait
# A new API container has a new address, and nginx only looks it up when it starts
docker compose restart frontend-react
docker compose ps

echo
echo "The Cheese App is running, after $((SECONDS - started)) s: http://${address:-<the VM external IP>}"
