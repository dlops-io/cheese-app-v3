import os
from pathlib import Path

import pulumi
import pulumi_gcp as gcp

# The manual deployment, automated: one VM that runs the same containers. There is no SSH and no key
# file: the VM runs as the app's service account, and startup.sh runs on it at every boot.
project = pulumi.Config("gcp").require("project")
# `pulumi config set vm:machine e2-standard-2` changes the machine
machine_type = pulumi.Config("vm").get("machine") or "n2d-standard-2"
region = os.environ["GCP_REGION"]
zone = os.environ["GCP_ZONE"]
app_name = "cheese-app-vm"
labels = {"app": app_name}
network_tag = app_name

# The registry and bucket come from the base stack, the images from the images stack
base = pulumi.StackReference(f"organization/cheese-app-base/{pulumi.get_stack()}")
images = pulumi.StackReference(f"organization/cheese-app-images/{pulumi.get_stack()}")

# Its own small network, which needs nothing from the project's default network
network = gcp.compute.Network(
    f"{app_name}-vpc",
    name=f"{app_name}-vpc",
    auto_create_subnetworks=False,
    description="VPC for the Cheese App VM",
)
subnet = gcp.compute.Subnetwork(
    f"{app_name}-subnet",
    name=f"{app_name}-subnet",
    ip_cidr_range="10.1.0.0/24",
    region=region,
    network=network.id,
)

# The web port, for everyone
gcp.compute.Firewall(
    f"{app_name}-allow-http",
    name=f"{app_name}-allow-http",
    network=network.id,
    allows=[gcp.compute.FirewallAllowArgs(protocol="tcp", ports=["80"])],
    source_ranges=["0.0.0.0/0"],
    target_tags=[network_tag],
)
# SSH only through Google's IAP proxy, which is what the console's SSH button can use
gcp.compute.Firewall(
    f"{app_name}-allow-ssh",
    name=f"{app_name}-allow-ssh",
    network=network.id,
    allows=[gcp.compute.FirewallAllowArgs(protocol="tcp", ports=["22"])],
    source_ranges=["35.235.240.0/20"],
    target_tags=[network_tag],
)

# A static IP, so the address stays the same when the VM is replaced
address = gcp.compute.Address(
    f"{app_name}-ip",
    name=f"{app_name}-ip",
    region=region,
    labels=labels,
)

# startup.sh, with this deployment's settings in front of it
startup_script = pulumi.Output.concat(
    "#!/bin/bash\n",
    "GCP_PROJECT=",
    project,
    "\n",
    "REGISTRY_HOST=",
    f"{region}-docker.pkg.dev",
    "\n",
    "API_IMAGE=",
    images.require_output("api_service_ref"),
    "\n",
    "FRONTEND_IMAGE=",
    images.require_output("frontend_react_ref"),
    "\n",
    "VECTOR_DB_CLI_IMAGE=",
    images.require_output("vector_db_cli_ref"),
    "\n",
    "CHAT_BUCKET=",
    base.require_output("chat_bucket"),
    "\n",
    Path("startup.sh").read_text(),
)

# New images change the script, and a changed script replaces the VM: the old one goes first, so the
# app is down for a few minutes. Kubernetes does this with no downtime.
instance = gcp.compute.Instance(
    app_name,
    name=app_name,
    machine_type=machine_type,
    zone=zone,
    tags=[network_tag],
    labels=labels,
    boot_disk=gcp.compute.InstanceBootDiskArgs(
        initialize_params=gcp.compute.InstanceBootDiskInitializeParamsArgs(
            image="debian-cloud/debian-12",
            size=50,
        ),
    ),
    network_interfaces=[
        gcp.compute.InstanceNetworkInterfaceArgs(
            subnetwork=subnet.id,
            access_configs=[gcp.compute.InstanceNetworkInterfaceAccessConfigArgs(nat_ip=address.address)],
        )
    ],
    service_account=gcp.compute.InstanceServiceAccountArgs(
        email=base.require_output("app_service_account"),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],  # IAM decides, not scopes
    ),
    metadata_startup_script=startup_script,
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)

# Export values
pulumi.export("instance_name", instance.name)
pulumi.export("instance_ip", address.address)
pulumi.export("zone", zone)
pulumi.export("app_url", pulumi.Output.concat("http://", address.address))
pulumi.export(
    "startup_log",
    pulumi.Output.concat(
        "gcloud compute instances get-serial-port-output ", instance.name, f" --zone {zone}"
    ),
)
