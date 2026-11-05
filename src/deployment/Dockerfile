FROM python:3.14-slim-trixie@sha256:fa99b65193ea9dbde3fc2367f43d3a2907571ce2a15213a86f0053e1d49d8456

# Every tool that builds images, runs the local cluster or talks to the cloud, at pinned versions, so
# Docker is the only thing a laptop needs. Built for the machine it runs on, like kind's nodes;
# deploy_images builds the amd64 images for GCP.
ARG TARGETARCH
ARG KIND_VERSION=v0.33.0
ARG KUBECTL_VERSION=v1.37.1
ARG PULUMI_VERSION=3.272.0
ARG UV_VERSION=0.13.6

ENV DEBIAN_FRONTEND=noninteractive \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/tmp/cheese-app-uv-cache \
    PATH=/opt/venv/bin:/usr/local/lib/pulumi:${PATH}

# Disable Pulumi passphrase prompts. Stack secrets are then protected only by who can read the state
# (the GCS bucket's IAM); switch to a gcpkms:// secrets provider before storing real ones.
ENV PULUMI_CONFIG_PASSPHRASE=""

RUN case "${TARGETARCH}" in amd64|arm64) ;; *) echo "Unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; esac
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg jq shellcheck \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=${TARGETARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian trixie stable" > /etc/apt/sources.list.d/docker.list \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /etc/apt/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-buildx-plugin \
        google-cloud-cli google-cloud-cli-gke-gcloud-auth-plugin \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSLo /tmp/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl" \
    && curl -fsSLo /tmp/kubectl.sha256 "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${TARGETARCH}/kubectl.sha256" \
    && echo "$(cat /tmp/kubectl.sha256)  /tmp/kubectl" | sha256sum --check \
    && install -m 0755 /tmp/kubectl /usr/local/bin/kubectl \
    && rm /tmp/kubectl /tmp/kubectl.sha256
# kind runs a Kubernetes cluster on this laptop, each node a container on the laptop's Docker
RUN cd /tmp \
    && curl -fsSLO "https://github.com/kubernetes-sigs/kind/releases/download/${KIND_VERSION}/kind-linux-${TARGETARCH}" \
    && curl -fsSLO "https://github.com/kubernetes-sigs/kind/releases/download/${KIND_VERSION}/kind-linux-${TARGETARCH}.sha256sum" \
    && sha256sum --check "kind-linux-${TARGETARCH}.sha256sum" \
    && install -m 0755 "kind-linux-${TARGETARCH}" /usr/local/bin/kind \
    && rm kind-linux-*
# Pulumi names amd64 "x64".
RUN arch="$([ "${TARGETARCH}" = amd64 ] && echo x64 || echo "${TARGETARCH}")" \
    && tarball="pulumi-v${PULUMI_VERSION}-linux-${arch}.tar.gz" \
    && base="https://github.com/pulumi/pulumi/releases/download/v${PULUMI_VERSION}" \
    && cd /tmp \
    && curl -fsSLO "${base}/${tarball}" \
    && curl -fsSLO "${base}/pulumi-${PULUMI_VERSION}-checksums.txt" \
    && grep " ${tarball}\$" "pulumi-${PULUMI_VERSION}-checksums.txt" | sha256sum --check \
    && tar -xzf "${tarball}" \
    && mv pulumi /usr/local/lib/pulumi \
    && rm "${tarball}" "pulumi-${PULUMI_VERSION}-checksums.txt" \
    && pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen && rm -rf "${UV_CACHE_DIR}"

# The entrypoint runs from the bind-mounted /app, so editing it needs no rebuild
ENTRYPOINT ["/bin/bash", "./docker-entrypoint.sh"]
