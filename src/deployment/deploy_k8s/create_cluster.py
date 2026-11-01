import pulumi
import pulumi_gcp as gcp
from pulumi import ResourceOptions

config = pulumi.Config("cluster")
security = pulumi.Config("security")
service_account_email = security.require("gcp_service_account_email")
app_service_account_email = security.require("app_service_account_email")
# A fixed number of nodes: pod scaling (the HPA) is fast and visible on its own, and the bill is known.
# `pulumi config set cluster:nodes 2` and `cluster:machine` change them.
node_count = config.get_int("nodes") or 3
machine_type = config.get("machine") or "e2-standard-2"
machine_disk_size = 50

# The namespace and name of the Kubernetes ServiceAccount the API runs as (k8s/api-service.yaml)
ksa_namespace = "cheese-app"
ksa_name = "api-service"


def create_cluster(project, zone, network, subnet, app_name):
    # Create a zonal GKE cluster (one control plane, covered by GKE's free tier) with private nodes,
    # Workload Identity (for Vertex AI and Cloud Storage without key files), the Gateway API, and no
    # default node pool
    cluster = gcp.container.Cluster(
        f"{app_name}-cluster",
        name=f"{app_name}-cluster",
        description="Cheese App GKE cluster",
        location=zone,
        deletion_protection=False,
        network=network.name,
        subnetwork=subnet.name,
        networking_mode="VPC_NATIVE",
        ip_allocation_policy={},  # let GKE create the pod and service ranges
        remove_default_node_pool=True,  # Remove default pool to use the node pool below
        initial_node_count=1,
        release_channel={"channel": "REGULAR"},
        private_cluster_config={
            "enable_private_nodes": True,  # Nodes use private IPs only
            "enable_private_endpoint": False,  # Control plane reachable from the deployment shell
            "master_ipv4_cidr_block": "172.16.0.0/28",  # CIDR for GKE control plane
        },
        workload_identity_config={"workload_pool": f"{project}.svc.id.goog"},
        gateway_api_config={"channel": "CHANNEL_STANDARD"},  # GatewayClasses for the Gateway/HTTPRoute
        resource_labels={"app": app_name},
    )

    # Create the node pool: fixed size, auto-repair, standard GCP service permissions
    node_pool = gcp.container.NodePool(
        f"{app_name}-pool",
        name=f"{app_name}-pool",
        cluster=cluster.name,
        location=zone,
        node_count=node_count,
        node_config=gcp.container.NodePoolNodeConfigArgs(
            service_account=service_account_email,
            machine_type=machine_type,
            image_type="cos_containerd",  # Container-Optimized OS with containerd runtime
            disk_size_gb=machine_disk_size,
            workload_metadata_config={"mode": "GKE_METADATA"},  # Workload Identity on these nodes
            oauth_scopes=["https://www.googleapis.com/auth/cloud-platform"],  # IAM decides, not scopes
            labels={"app": app_name},
        ),
        management=gcp.container.NodePoolManagementArgs(auto_repair=True, auto_upgrade=True),
        opts=ResourceOptions(depends_on=[cluster]),
    )

    # Workload Identity: pods running as the API's Kubernetes ServiceAccount act as this Google service
    # account, so they reach Vertex AI and Cloud Storage with no key file in the cluster
    gcp.serviceaccount.IAMMember(
        f"{app_name}-workload-identity",
        service_account_id=f"projects/{project}/serviceAccounts/{app_service_account_email}",
        role="roles/iam.workloadIdentityUser",
        member=f"serviceAccount:{project}.svc.id.goog[{ksa_namespace}/{ksa_name}]",
        opts=ResourceOptions(depends_on=[cluster]),  # the identity pool exists once the cluster does
    )

    return cluster, node_pool
