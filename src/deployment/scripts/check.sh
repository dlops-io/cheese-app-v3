#!/usr/bin/env bash
# Lint the deployment tooling: shell scripts and Python (Pulumi programs).
set -euo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
mapfile -t scripts < <(find . \( -path ./.local -o -path ./.venv -o -path ./pulumi-plugins -o -path ./docker-config \) -prune -o -name '*.sh' -print | sort)
for script in "${scripts[@]}"; do
    bash -n "${script}"
done
shellcheck -x --source-path=SCRIPTDIR "${scripts[@]}"
ruff check .
ruff format --check .
echo "check.sh: all checks passed"
