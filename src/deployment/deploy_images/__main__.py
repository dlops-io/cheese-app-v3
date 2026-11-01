import hashlib
from pathlib import Path

import pulumi
import pulumi_docker_build as docker_build
from pulumi import CustomTimeouts

# The registry comes from the long-lived base stack
base = pulumi.StackReference(f"organization/cheese-app-base/{pulumi.get_stack()}")
registry_url = base.require_output("registry")

# Each image's folder; its production Dockerfile sits there
SERVICES = ["api-service", "frontend-react", "vector-db"]
# Never part of an image (and the same as the services' .dockerignore files)
SKIP = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".DS_Store",
    "docker-volumes",
    "outputs",
}


def content_tag(context: Path) -> str:
    """A tag from the service's files: unchanged code keeps its tag (and running pods), any change gets a
    new one. A timestamp would roll every pod on every `pulumi up`, a git commit would miss local edits."""
    digest = hashlib.sha256()
    for path in sorted(context.rglob("*")):
        if path.is_file() and not SKIP.intersection(path.relative_to(context).parts):
            digest.update(str(path.relative_to(context)).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()[:12]


for service in SERVICES:
    # ../../<service> is the service's mount in the deployment container (/api-service, ...)
    context_path = Path("../..") / service
    name = "cheese-app-vector-db-cli" if service == "vector-db" else f"cheese-app-{service}"
    image = docker_build.Image(
        f"build-{name}",
        tags=[pulumi.Output.concat(registry_url, "/", name, ":", content_tag(context_path))],
        context=docker_build.BuildContextArgs(location=str(context_path)),
        dockerfile=docker_build.DockerfileArgs(location=str(context_path / "Dockerfile")),
        platforms=[docker_build.Platform.LINUX_AMD64],  # GKE nodes are amd64
        push=True,
        opts=pulumi.ResourceOptions(custom_timeouts=CustomTimeouts(create="30m"), retain_on_delete=True),
    )
    # Export references to stack: the digest-pinned ref is what the workloads deploy
    key = "vector_db_cli" if service == "vector-db" else service.replace("-", "_")
    pulumi.export(f"{key}_ref", image.ref)
