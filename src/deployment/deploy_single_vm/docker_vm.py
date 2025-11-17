import os
import pulumi
import pulumi_gcp as gcp
from pulumi import ResourceOptions
from pulumi_command import remote
import pulumi_docker as docker
import hashlib


# Get project info and configuration
gcp_config = pulumi.Config("gcp")
project = gcp_config.require("project")
location = os.environ["GCP_REGION"]
zone = os.environ["GCP_ZONE"]
ssh_user = "sa_100110341521630214262"
gcp_service_account_email = "deployment@ac215-project.iam.gserviceaccount.com"

# Configuration variables
persistent_disk_name = "cheese-app-demo-disk-pulumi"
persistent_disk_size = 50
machine_instance_name = "cheese-app-demo-pulumi"
machine_type = "n2d-standard-2"
machine_disk_size = 50


def load_ssh_key_pair():
    """Load SSH keys for remote access"""
    with open("/secrets/ssh-key-deployment", "r") as private_key_file:
        private_key = private_key_file.read()
    with open("/secrets/ssh-key-deployment.pub", "r") as public_key_file:
        public_key = public_key_file.read()
    return private_key, public_key


private_key, ssh_public_key = load_ssh_key_pair()

# Create a new network with auto-created subnetworks
network = gcp.compute.Network(
    "cheese-app-network-pulumi",
    name="cheese-app-network-pulumi",
    auto_create_subnetworks=True,
)

# Create firewall rule for HTTP traffic
firewall_http = gcp.compute.Firewall(
    "allow-http-pulumi",
    network=network.self_link,
    allows=[
        gcp.compute.FirewallAllowArgs(
            protocol="tcp",
            ports=["80"],
        )
    ],
    source_ranges=["0.0.0.0/0"],
    target_tags=["http-server-pulumi"],
)

# Create firewall rule for HTTPS traffic
firewall_https = gcp.compute.Firewall(
    "allow-https-pulumi",
    network=network.self_link,
    allows=[
        gcp.compute.FirewallAllowArgs(
            protocol="tcp",
            ports=["443"],
        )
    ],
    source_ranges=["0.0.0.0/0"],
    target_tags=["https-server-pulumi"],
)

# Create firewall rule for SSH
firewall_ssh = gcp.compute.Firewall(
    "allow-ssh-pulumi",
    network=network.self_link,
    allows=[
        gcp.compute.FirewallAllowArgs(
            protocol="tcp",
            ports=["22"],
        )
    ],
    source_ranges=["0.0.0.0/0"],
)

# Create persistent disk for data storage
persistent_disk = gcp.compute.Disk(
    persistent_disk_name,
    zone=zone,
    size=persistent_disk_size,
    type="pd-standard",
)

# Resolve the latest Ubuntu 22.04 LTS image from the public Ubuntu project
ubuntu_image = gcp.compute.get_image(
    family="ubuntu-2204-lts",
    project="ubuntu-os-cloud",
)

# Create the VM instance
instance = gcp.compute.Instance(
    machine_instance_name,
    name=machine_instance_name,
    machine_type=machine_type,
    zone=zone,
    boot_disk=gcp.compute.InstanceBootDiskArgs(
        initialize_params=gcp.compute.InstanceBootDiskInitializeParamsArgs(
            image=ubuntu_image.self_link,
            size=machine_disk_size,
        ),
    ),
    # Attach persistent disk
    attached_disks=[
        gcp.compute.InstanceAttachedDiskArgs(
            source=persistent_disk.id,
        )
    ],
    network_interfaces=[
        gcp.compute.InstanceNetworkInterfaceArgs(
            network=network.id,
            # Let GCP auto-assign an ephemeral IP
            access_configs=[
                gcp.compute.InstanceNetworkInterfaceAccessConfigArgs(
                    network_tier="STANDARD"
                )
            ],
        )
    ],
    metadata={
        "ssh-keys": f"{ssh_user}:{ssh_public_key}",
        "enable-oslogin": "FALSE",
    },
    tags=["http-server-pulumi", "https-server-pulumi"],
    service_account=gcp.compute.InstanceServiceAccountArgs(
        email=gcp_service_account_email,
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
        depends_on=[firewall_http, firewall_https, firewall_ssh, persistent_disk]
    ),
)

# Get the VM's public IP address (dynamically assigned)
instance_ip = instance.network_interfaces.apply(
    lambda interfaces: interfaces[0].access_configs[0].nat_ip
)

# Create SSH connection configuration for remote commands
connection = remote.ConnectionArgs(
    host=instance_ip,
    user=ssh_user,
    private_key=private_key,
)

# Provision VM: Format and mount persistent disk
format_disk = remote.Command(
    "format-persistent-disk",
    connection=connection,
    create="""
        # Format disk only if it doesn't have a filesystem
        sudo sh -c 'blkid -o value -s TYPE /dev/disk/by-id/google-persistent-disk-1 || mkfs.ext4 /dev/disk/by-id/google-persistent-disk-1'
    """,
    opts=ResourceOptions(depends_on=[instance]),
)

create_mount_dir = remote.Command(
    "create-mount-directory",
    connection=connection,
    create="""
        sudo mkdir -p /mnt/disk-1
        sudo chown root:root /mnt/disk-1
        sudo chmod 0755 /mnt/disk-1
    """,
    opts=ResourceOptions(depends_on=[format_disk]),
)

mount_disk = remote.Command(
    "mount-persistent-disk",
    connection=connection,
    create="""
        # Add to fstab if not already present
        if ! grep -q '/mnt/disk-1' /etc/fstab; then
            echo '/dev/disk/by-id/google-persistent-disk-1 /mnt/disk-1 ext4 discard,defaults 0 2' | sudo tee -a /etc/fstab
        fi
        # Mount the disk
        sudo mount -a
    """,
    opts=ResourceOptions(depends_on=[create_mount_dir]),
)

# Provision VM: Disable unattended upgrades and update system
disable_unattended_upgrades = remote.Command(
    "disable-unattended-upgrades",
    connection=connection,
    create="""
        sudo systemctl disable --now apt-daily.timer || true
        sudo systemctl disable --now apt-daily-upgrade.timer || true
        sudo systemctl daemon-reload
        sudo systemd-run --property="After=apt-daily.service apt-daily-upgrade.service" --wait /bin/true
    """,
    opts=ResourceOptions(depends_on=[mount_disk]),
)

# Provision VM: Update apt and install dependencies
update_system = remote.Command(
    "update-system",
    connection=connection,
    create="""
        sudo apt-get update
        sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
    """,
    opts=ResourceOptions(depends_on=[disable_unattended_upgrades]),
)

install_dependencies = remote.Command(
    "install-dependencies",
    connection=connection,
    create="""
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
            apt-transport-https \
            ca-certificates \
            curl \
            gnupg-agent \
            software-properties-common \
            python3-setuptools \
            python3-pip \
            lsb-release
    """,
    opts=ResourceOptions(depends_on=[update_system]),
)

# Install gcloud (needed for gcloud auth commands later)
install_gcloud = remote.Command(
    "install-gcloud",
    connection=connection,
    create="""
        if ! command -v gcloud >/dev/null 2>&1; then
            # Try installing Google Cloud SDK via apt
            sudo DEBIAN_FRONTEND=noninteractive apt-get install -y google-cloud-cli || \
            sudo DEBIAN_FRONTEND=noninteractive apt-get install -y google-cloud-sdk || true
        fi
    """,
    opts=ResourceOptions(depends_on=[install_dependencies]),
)

# Provision VM: Install Docker
install_docker = remote.Command(
    "install-docker",
    connection=connection,
    create="""
        # Get distributor ID and release
        DISTRO=$(lsb_release -is | tr '[:upper:]' '[:lower:]')
        RELEASE=$(lsb_release -cs)

        # Add Docker GPG key
        curl -fsSL https://download.docker.com/linux/$DISTRO/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

        # Add Docker repository
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/$DISTRO $RELEASE stable" | \
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        # Install Docker
        sudo apt-get update
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io
    """,
    opts=ResourceOptions(depends_on=[install_gcloud]),
)

# Provision VM: Install Python packages for Docker management
install_pip_packages = remote.Command(
    "install-pip-packages",
    connection=connection,
    create="""
        sudo pip3 install requests docker
    """,
    opts=ResourceOptions(depends_on=[install_docker]),
)

# Provision VM: Configure Docker
configure_docker = remote.Command(
    "configure-docker",
    connection=connection,
    create=f"""
        # Create docker group
        sudo groupadd docker || true

        # Add current user to docker group
        sudo usermod -aG docker {ssh_user} || true
        newgrp docker || true
        

        # Authenticate Docker with GCP (using instance service account)
        if command -v gcloud >/dev/null 2>&1; then
            gcloud auth configure-docker --quiet || true
            gcloud auth configure-docker us-docker.pkg.dev --quiet || true
        fi

        # Start and enable Docker service
        sudo systemctl start docker
        sudo systemctl enable docker

        # Fix docker socket permissions
        sudo chmod 666 /var/run/docker.sock
    """,
    opts=ResourceOptions(depends_on=[install_pip_packages]),
)

# Setup Containers

# Get image references from deploy_images stack
# For local backend, use: "organization/project/stack"
images_stack = pulumi.StackReference("organization/deploy-images/dev")
# Get the image tags (these are arrays, so we take the first element)
api_service_tag = images_stack.get_output("cheese-app-api-service-tags")
frontend_tag = images_stack.get_output("cheese-app-frontend-react-tags")
vector_db_cli_tag = images_stack.get_output("cheese-app-vector-db-cli-tags")

# Setup GCP secrets for containers
copy_secrets = remote.Command(
    "copy-gcp-secrets",
    connection=connection,
    create="""
        sudo mkdir -p /srv/secrets
        sudo chmod 0755 /srv/secrets
    """,
    opts=ResourceOptions(depends_on=[configure_docker]),
)

upload_service_account = remote.CopyToRemote(
    "upload-service-account-key",
    connection=connection,
    source=pulumi.FileAsset("/secrets/gcp-service.json"),
    remote_path="/tmp/gcp-service.json",
    opts=ResourceOptions(depends_on=[copy_secrets]),
)

move_secrets = remote.Command(
    "move-secrets-to-srv",
    connection=connection,
    create="""
        sudo mv /tmp/gcp-service.json /srv/secrets/gcp-service.json
        sudo chmod 0644 /srv/secrets/gcp-service.json
        sudo chown root:root /srv/secrets/gcp-service.json
        if command -v gcloud >/dev/null 2>&1; then
            gcloud auth activate-service-account --key-file /srv/secrets/gcp-service.json || true
            gcloud auth configure-docker us-docker.pkg.dev --quiet || true
        fi
    """,
    opts=ResourceOptions(depends_on=[upload_service_account]),
)
# Create directories on persistent disk
create_dirs = remote.Command(
    "create-persistent-directories",
    connection=connection,
    create="""
        sudo mkdir -p /mnt/disk-1/persistent
        sudo mkdir -p /mnt/disk-1/chromadb
        sudo chmod 0777 /mnt/disk-1/persistent
        sudo chmod 0777 /mnt/disk-1/chromadb
    """,
    opts=ResourceOptions(depends_on=[move_secrets]),
)

give_docker_access = remote.Command(
    "give-docker-access",
    connection=connection,
    create=f"""
        sudo adduser {ssh_user} docker || true
        sudo usermod -aG docker {ssh_user} || true
        newgrp docker || true
    """,
    opts=ResourceOptions(depends_on=[move_secrets]),
)

# Set up Docker provider with SSH credentials for remote access
docker_provider = docker.Provider(
    "docker-provider",
    host=instance_ip.apply(lambda ip: f"ssh://{ssh_user}@{ip}"),
    # SSH options to handle key-based authentication and suppress host checking
    ssh_opts=[
        "-i",
        "/secrets/ssh-key-deployment",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
    ],
    # Authentication for Google Container Registry / Artifact Registry
    registry_auth=[
        {
            "address": "us-docker.pkg.dev",
            # "config_file": "~/.docker/config.json",
        }
    ],
    opts=ResourceOptions(depends_on=[install_docker, give_docker_access]),
)


# Create a Docker network for container communication
docker_network = docker.Network(
    "appnetwork",
    name="appnetwork",
    driver="bridge",  # Standard bridge network
    opts=ResourceOptions(
        provider=docker_provider,
        depends_on=[install_docker],
    ),
)

# Frontend
deploy_frontend_container = docker.Container(
    "frontend-container",
    image=frontend_tag.apply(lambda tags: tags[0]),
    name="frontend",
    # Map container port to host port
    ports=[
        docker.ContainerPortArgs(
            internal=3000,  # Container port
            external=3000,  # Host port
        )
    ],
    # Connect to the app network for inter-container communication
    networks_advanced=[
        docker.ContainerNetworksAdvancedArgs(
            name=docker_network.name,
        ),
    ],
    opts=ResourceOptions(
        provider=docker_provider,
        depends_on=[docker_network, create_dirs],
    ),
)

deploy_vector_db_container = docker.Container(
    "vector-db-container",
    image="chromadb/chroma:latest",
    name="vector-db",
    restart="always",
    # Map container port to host port
    ports=[
        docker.ContainerPortArgs(
            internal=8000,  # Container port
            external=8000,  # Host port
        )
    ],
    # Environment variables for the container
    envs=[
        "IS_PERSISTENT=TRUE",
        "ANONYMIZED_TELEMETRY=FALSE",
    ],
    # Mount persistent volume for ChromaDB data
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/mnt/disk-1/chromadb",
            container_path="/chroma/chroma",
            read_only=False,
        )
    ],
    # Connect to the app network for inter-container communication
    networks_advanced=[
        docker.ContainerNetworksAdvancedArgs(
            name=docker_network.name,
        ),
    ],
    opts=ResourceOptions(
        provider=docker_provider,
        depends_on=[docker_network, create_dirs],
    ),
)

load_vector_db = docker.Container(
    "load-vector-db-data",
    image=vector_db_cli_tag.apply(lambda tags: tags[0]),
    name="vector-db-loader",
    # Equivalent to: --rm
    rm=True,
    restart="no",
    # Env variables from CLI
    envs=[
        f"GCP_PROJECT={project}",
        "CHROMADB_HOST=vector-db",
        "CHROMADB_PORT=8000",
        "GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-service.json",
    ],
    # Equivalent to: -v /srv/secrets:/secrets
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/srv/secrets",
            container_path="/secrets",
            read_only=False,
        )
    ],
    # Equivalent to: --network appnetwork
    networks_advanced=[
        docker.ContainerNetworksAdvancedArgs(
            name=docker_network.name,
        )
    ],
    # Equivalent to: cli.py --download --load --chunk_type recursive-split
    command=[
        "cli.py",
        "--download",
        "--load",
        "--chunk_type",
        "recursive-split",
    ],
    opts=ResourceOptions(
        provider=docker_provider,
        depends_on=[deploy_vector_db_container],
    ),
)

deploy_api_service = docker.Container(
    "deploy-api-service-container",
    image=api_service_tag.apply(lambda tags: tags[0]),
    name="api-service",
    # Equivalent of: --restart always
    restart="always",
    # Equivalent of: -p 9000:9000
    ports=[
        docker.ContainerPortArgs(
            internal=9000,
            external=9000,
        )
    ],
    # Environment variables
    envs=[
        "GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-service.json",
        f"GCP_PROJECT={project}",
        "GCS_BUCKET_NAME=cheese-app-models",
        "CHROMADB_HOST=vector-db",
        "CHROMADB_PORT=8000",
    ],
    # Volumes
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/mnt/disk-1/persistent",
            container_path="/persistent",
            read_only=False,
        ),
        docker.ContainerVolumeArgs(
            host_path="/srv/secrets",
            container_path="/secrets",
            read_only=False,
        ),
    ],
    # Network
    networks_advanced=[
        docker.ContainerNetworksAdvancedArgs(
            name=docker_network.name,
        )
    ],
    opts=ResourceOptions(
        provider=docker_provider,
        depends_on=[load_vector_db],
    ),
)

# Setup Nginx Webserver

# Shared asset for nginx config
nginx_conf_asset = pulumi.FileAsset("../nginx-conf/nginx/nginx.conf")


def file_checksum(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


checksum = file_checksum("../nginx-conf/nginx/nginx.conf")

# Create nginx config directory
create_nginx_conf_dir = remote.Command(
    "create-nginx-conf-directory",
    connection=connection,
    create="""
        sudo mkdir -p /conf/nginx
        sudo chmod 0755 /conf/nginx
    """,
    opts=ResourceOptions(depends_on=[deploy_api_service]),
)

# Copy nginx configuration file
upload_nginx_conf = remote.CopyToRemote(
    "upload-nginx-conf",
    connection=connection,
    source=nginx_conf_asset,
    remote_path="/tmp/nginx.conf",
    triggers=[checksum],
    opts=ResourceOptions(depends_on=[create_nginx_conf_dir]),
)

# Move nginx config to final location
move_nginx_conf = remote.Command(
    "move-nginx-conf",
    connection=connection,
    create="""
        sudo mv /tmp/nginx.conf /conf/nginx/nginx.conf
        sudo chmod 0644 /conf/nginx/nginx.conf
        sudo chown root:root /conf/nginx/nginx.conf
    """,
    triggers=[checksum],
    opts=ResourceOptions(depends_on=[upload_nginx_conf]),
)

deploy_nginx = docker.Container(
    "deploy-nginx-container",
    image="nginx:stable",
    name="nginx",
    # Equivalent of: --restart always
    restart="always",
    # Equivalent of: -p 80:80 -p 443:443
    ports=[
        docker.ContainerPortArgs(
            internal=80,
            external=80,
        ),
        docker.ContainerPortArgs(
            internal=443,
            external=443,
        ),
    ],
    # Mount nginx config
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/conf/nginx/nginx.conf",
            container_path="/etc/nginx/nginx.conf",
            read_only=True,
        )
    ],
    # Network
    networks_advanced=[
        docker.ContainerNetworksAdvancedArgs(
            name=docker_network.name,
        )
    ],
    opts=ResourceOptions(
        provider=docker_provider,
        depends_on=[move_nginx_conf],
    ),
)

# Restart nginx to ensure config is loaded
restart_nginx = remote.Command(
    "restart-nginx-container",
    connection=connection,
    create="""
        sudo docker container restart nginx
    """,
    triggers=[checksum],
    opts=ResourceOptions(depends_on=[deploy_nginx, upload_nginx_conf]),
)

# Export references to stack
pulumi.export("instance_name", instance.name)
pulumi.export("instance_ip", instance_ip)
pulumi.export("zone", zone)
pulumi.export("persistent_disk_name", persistent_disk.name)
pulumi.export("ssh_user", ssh_user)
pulumi.export("ssh_command", instance_ip.apply(lambda ip: f"ssh {ssh_user}@{ip}"))
