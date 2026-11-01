import os

import pulumi
import pulumi_gcp as gcp

# The pieces that outlive the cluster. They live in their own stack, so the cluster can be destroyed
# and recreated without the address changing or your images and chats disappearing.
project = pulumi.Config("gcp").require("project")
app_service_account = pulumi.Config("security").require("app_service_account_email")
region = os.environ["GCP_REGION"]
app_name = "cheese-app"
labels = {"app": app_name}

# The Gateway's IP. Global, because the gke-l7-global-external-managed load balancer is; the Gateway
# asks for it by name (spec.addresses: NamedAddress).
gateway_ip = gcp.compute.GlobalAddress(
    f"{app_name}-gateway-ip",
    name=f"{app_name}-gateway-ip",
    description="Cheese App GKE Gateway",
    labels=labels,
)

# Where the images go: api-service, frontend-react and vector-db-cli
registry = gcp.artifactregistry.Repository(
    f"{app_name}-registry",
    repository_id=app_name,
    location=region,
    format="DOCKER",
    description="Cheese App images",
    labels=labels,
)

# The chat history: outside the pods, so any copy of the API can continue any chat
chat_bucket = gcp.storage.Bucket(
    f"{app_name}-chats",
    name=f"{project}-{app_name}-chats",
    location=region,
    uniform_bucket_level_access=True,
    force_destroy=True,  # `pulumi destroy` here removes the chats too
    labels=labels,
)
gcp.storage.BucketIAMMember(
    f"{app_name}-chats-access",
    bucket=chat_bucket.name,
    role="roles/storage.objectAdmin",
    member=f"serviceAccount:{app_service_account}",
)

# Export values
pulumi.export("gateway_ip", gateway_ip.address)
pulumi.export("gateway_ip_name", gateway_ip.name)
pulumi.export(
    "registry", pulumi.Output.concat(region, "-docker.pkg.dev/", project, "/", registry.repository_id)
)
pulumi.export("chat_bucket", chat_bucket.name)
pulumi.export("app_service_account", app_service_account)
