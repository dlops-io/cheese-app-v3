import os
import pulumi
import pulumi_gcp as gcp
import pulumi_docker as docker
from pulumi import ResourceOptions
from pulumi_command import remote

# 🔧 Get project info
project = pulumi.Config("gcp").require("project")
location = os.environ["GCP_REGION"]
zone = os.environ["GCP_ZONE"]
ssh_user = "sa_100110341521630214262"


def load_ssh_key_pair():
    """Load SSH keys"""
    with open("/secrets/ssh-key-deployment", "r") as private_key_file:
        private_key = private_key_file.read()
    with open("/secrets/ssh-key-deployment.pub", "r") as public_key_file:
        public_key = public_key_file.read()
    return private_key, public_key


private_key, ssh_public_key = load_ssh_key_pair()

# Create a new network
network = gcp.compute.Network(
    "network",
    auto_create_subnetworks=True,
)

# Create a firewall rule to allow required traffic
firewall = gcp.compute.Firewall(
    "allow-ssh",
    network=network.self_link,
    allows=[
        gcp.compute.FirewallAllowArgs(
            protocol="tcp",
            ports=[
                "22",  # SSH
                "80",  # HTTP
                "3000",  # Frontend service
                "9000",  # API service
            ],
        )
    ],
    source_ranges=["0.0.0.0/0"],  # Allow access from any IP
)

# Create the VM instance
instance = gcp.compute.Instance(
    "instance",
    machine_type="e2-medium",  # 2 vCPUs, 4GB memory
    zone=zone,
    boot_disk=gcp.compute.InstanceBootDiskArgs(
        initialize_params=gcp.compute.InstanceBootDiskInitializeParamsArgs(
            image="ubuntu-os-cloud/ubuntu-2004-lts",  # Ubuntu 20.04 LTS
        ),
    ),
    network_interfaces=[
        gcp.compute.InstanceNetworkInterfaceArgs(
            network=network.id,
            # Provision an external IP for public access
            access_configs=[
                gcp.compute.InstanceNetworkInterfaceAccessConfigArgs(
                    nat_ip="35.209.93.249", network_tier="STANDARD"
                )
            ],
        )
    ],
    metadata={
        "ssh-keys": f"{ssh_user}:{ssh_public_key}"  # Add SSH public key for remote access
    },
    service_account=gcp.compute.InstanceServiceAccountArgs(
        email="gcp-service-account@myinstel-dev.iam.gserviceaccount.com",
        # Required scopes for GCP service interaction
        scopes=[
            "https://www.googleapis.com/auth/devstorage.read_only",
            "https://www.googleapis.com/auth/logging.write",
            "https://www.googleapis.com/auth/monitoring.write",
            "https://www.googleapis.com/auth/service.management.readonly",
            "https://www.googleapis.com/auth/servicecontrol",
            "https://www.googleapis.com/auth/trace.append",
        ],
    ),
    opts=ResourceOptions(
        depends_on=[firewall]
    ),  # Ensure firewall exists before creating instance
)

# Get the VM's public IP address
instance_ip = instance.network_interfaces.apply(
    lambda interfaces: interfaces[0].access_configs[0].nat_ip
)


# Configure the SSH connection to the VM

# Install Docker on the VM using remote commands
