# import os
# import pulumi
# import pulumi_gcp as gcp
# import pulumi_kubernetes as k8s
# from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
# from pulumi import Output

# # Get project info and configuration
# gcp_config = pulumi.Config("gcp")
# project = gcp_config.require("project")
# location = os.environ["GCP_REGION"]
# zone = os.environ["GCP_ZONE"]

# # Cluster configuration
# cluster_name = "cheese-app-cluster"
# machine_type = "n2d-standard-2"
# machine_disk_size = 30
# initial_node_count = 2

# # Get the image tag from the deploy_images stack
# stack_ref = pulumi.StackReference(f"organization/{project}/deploy_images/dev")
# # You can get outputs from the deploy_images stack like this:
# # api_service_image_ref = stack_ref.get_output("cheese-app-api-service-ref")
# # For now, we'll use a placeholder or environment variable for the tag
# docker_tag = os.environ.get("DOCKER_TAG", "latest")

# # 1. Create GKE Cluster (update this)
# cluster = gcp.container.Cluster(
#     cluster_name,
#     name=cluster_name,
#     location=zone,
#     initial_node_count=initial_node_count,
#     remove_default_node_pool=True,  # We'll create a custom node pool
#     release_channel=gcp.container.ClusterReleaseChannelArgs(
#         channel="UNSPECIFIED",
#     ),
#     ip_allocation_policy=gcp.container.ClusterIpAllocationPolicyArgs(
#         cluster_ipv4_cidr_block="",
#         services_ipv4_cidr_block="",
#     ),
#     deletion_protection=False,  # Set to True in production
# )

# # 2. Create Node Pool (update this)
# node_pool = gcp.container.NodePool(
#     "default-pool",
#     cluster=cluster.name,
#     location=zone,
#     initial_node_count=initial_node_count,
#     node_config=gcp.container.NodePoolNodeConfigArgs(
#         machine_type=machine_type,
#         image_type="cos_containerd",
#         disk_size_gb=machine_disk_size,
#         oauth_scopes=[
#             "https://www.googleapis.com/auth/devstorage.read_only",
#             "https://www.googleapis.com/auth/logging.write",
#             "https://www.googleapis.com/auth/monitoring",
#             "https://www.googleapis.com/auth/servicecontrol",
#             "https://www.googleapis.com/auth/service.management.readonly",
#             "https://www.googleapis.com/auth/trace.append",
#         ],
#     ),
#     autoscaling=gcp.container.NodePoolAutoscalingArgs(
#         min_node_count=1,
#         max_node_count=initial_node_count,
#     ),
#     management=gcp.container.NodePoolManagementArgs(
#         auto_repair=True,
#         auto_upgrade=True,
#     ),
# )

# # Create a Kubernetes provider instance that uses the GKE cluster (update this)
# k8s_provider = k8s.Provider(
#     "gke-k8s",
#     kubeconfig=Output.all(cluster.name, cluster.endpoint, cluster.master_auth).apply(
#         lambda args: f"""apiVersion: v1
# clusters:
# - cluster:
#     certificate-authority-data: {args[2].cluster_ca_certificate}
#     server: https://{args[1]}
#   name: {args[0]}
# contexts:
# - context:
#     cluster: {args[0]}
#     user: {args[0]}
#   name: {args[0]}
# current-context: {args[0]}
# kind: Config
# preferences: {{}}
# users:
# - name: {args[0]}
#   user:
#     exec:
#       apiVersion: client.authentication.k8s.io/v1beta1
#       command: gke-gcloud-auth-plugin
#       installHint: Install gke-gcloud-auth-plugin for use with kubectl by following
#         https://cloud.google.com/blog/products/containers-kubernetes/kubectl-auth-changes-in-gke
#       provideClusterInfo: true
# """
#     ),
#     opts=pulumi.ResourceOptions(depends_on=[node_pool]),
# )

# # 3. Create Namespace
# namespace = k8s.core.v1.Namespace(
#     f"{cluster_name}-namespace",
#     metadata=k8s.meta.v1.ObjectMetaArgs(
#         name=f"{cluster_name}-namespace",
#     ),
#     opts=pulumi.ResourceOptions(provider=k8s_provider),
# )

# # 4. Install nginx-ingress using Helm
# nginx_ingress = Chart(
#     "nginx-ingress",
#     ChartOpts(
#         chart="nginx-ingress",
#         version="1.1.3",  # Specify version for reproducibility
#         fetch_opts=FetchOpts(
#             repo="https://helm.nginx.com/stable",
#         ),
#         namespace=namespace.metadata.name,
#     ),
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
# )

# # 5. Create Persistent Volume Claims
# persistent_pvc = k8s.core.v1.PersistentVolumeClaim(
#     "persistent-pvc",
#     metadata=k8s.meta.v1.ObjectMetaArgs(
#         name="persistent-pvc",
#         namespace=namespace.metadata.name,
#     ),
#     spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
#         access_modes=["ReadWriteOnce"],
#         resources=k8s.core.v1.VolumeResourceRequirementsArgs(
#             requests={"storage": "5Gi"},
#         ),
#     ),
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
# )

# chromadb_pvc = k8s.core.v1.PersistentVolumeClaim(
#     "chromadb-pvc",
#     metadata=k8s.meta.v1.ObjectMetaArgs(
#         name="chromadb-pvc",
#         namespace=namespace.metadata.name,
#     ),
#     spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
#         access_modes=["ReadWriteOnce"],
#         resources=k8s.core.v1.VolumeResourceRequirementsArgs(
#             requests={"storage": "10Gi"},
#         ),
#     ),
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
# )

# # 6. Create Secret for GCP Service Account
# # Note: In Pulumi, you need to read the file and create the secret
# # Make sure the path to your GCP service account JSON is correct

# # KSA (Kubernetes Service Account) to be used by the API service
# gcp_service_key_path = "../secrets/gcp-service.json"
# # try:
# #     with open(gcp_service_key_path, "r") as f:
# #         gcp_service_key_content = f.read()

# #     gcp_secret = k8s.core.v1.Secret(
# #         "gcp-service-key",
# #         metadata=k8s.meta.v1.ObjectMetaArgs(
# #             name="gcp-service-key",
# #             namespace=namespace.metadata.name,
# #         ),
# #         string_data={
# #             "gcp-service.json": gcp_service_key_content,
# #         },
# #         opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
# #     )
# # except FileNotFoundError:
# #     pulumi.log.warn(f"GCP service key file not found at {gcp_service_key_path}. Please ensure it exists before deploying.")
# #     gcp_secret = None

# # 7. Create Deployments

# # Frontend Deployment stack referece
# frontend_deployment = k8s.apps.v1.Deployment(
#     "frontend",
#     metadata=k8s.meta.v1.ObjectMetaArgs(
#         name="frontend",
#         namespace=namespace.metadata.name,
#     ),
#     spec=k8s.apps.v1.DeploymentSpecArgs(
#         selector=k8s.meta.v1.LabelSelectorArgs(
#             match_labels={"run": "frontend"},
#         ),
#         template=k8s.core.v1.PodTemplateSpecArgs(
#             metadata=k8s.meta.v1.ObjectMetaArgs(
#                 labels={"run": "frontend"},
#             ),
#             spec=k8s.core.v1.PodSpecArgs(
#                 containers=[
#                     k8s.core.v1.ContainerArgs(
#                         name="frontend",
#                         image=f"us-docker.pkg.dev/{project}/cheese-app-repository/cheese-app-frontend-react:{docker_tag}",
#                         image_pull_policy="IfNotPresent",
#                         ports=[k8s.core.v1.ContainerPortArgs(
#                             container_port=3000,
#                             protocol="TCP",
#                         )],
#                     ),
#                 ],
#             ),
#         ),
#     ),
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
# )

# # ChromaDB Deployment
# vector_db_deployment = k8s.apps.v1.Deployment(
#     "vector-db",
#     metadata=k8s.meta.v1.ObjectMetaArgs(
#         name="vector-db",
#         namespace=namespace.metadata.name,
#     ),
#     spec=k8s.apps.v1.DeploymentSpecArgs(
#         selector=k8s.meta.v1.LabelSelectorArgs(
#             match_labels={"run": "vector-db"},
#         ),
#         template=k8s.core.v1.PodTemplateSpecArgs(
#             metadata=k8s.meta.v1.ObjectMetaArgs(
#                 labels={"run": "vector-db"},
#             ),
#             spec=k8s.core.v1.PodSpecArgs(
#                 containers=[
#                     k8s.core.v1.ContainerArgs(
#                         name="vector-db",
#                         image="chromadb/chroma:0.5.6",
#                         ports=[k8s.core.v1.ContainerPortArgs(
#                             container_port=8000,
#                             protocol="TCP",
#                         )],
#                         env=[
#                             k8s.core.v1.EnvVarArgs(name="IS_PERSISTENT", value="TRUE"),
#                             k8s.core.v1.EnvVarArgs(name="ANONYMIZED_TELEMETRY", value="FALSE"),
#                         ],
#                         # Uncomment below to use persistent volume
#                         # volume_mounts=[
#                         #     k8s.core.v1.VolumeMountArgs(
#                         #         name="chromadb-storage",
#                         #         mount_path="/chroma/chroma",
#                         #     ),
#                         # ],
#                     ),
#                 ],
#                 # volumes=[
#                 #     k8s.core.v1.VolumeArgs(
#                 #         name="chromadb-storage",
#                 #         persistent_volume_claim=k8s.core.v1.PersistentVolumeClaimVolumeSourceArgs(
#                 #             claim_name=chromadb_pvc.metadata.name,
#                 #         ),
#                 #     ),
#                 # ],
#             ),
#         ),
#     ),
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace, chromadb_pvc]),
# )

# # API Service Deployment
# api_deployment_deps = [namespace, persistent_pvc]
# if gcp_secret:
#     api_deployment_deps.append(gcp_secret)

# api_deployment = k8s.apps.v1.Deployment(
#     "api",
#     metadata=k8s.meta.v1.ObjectMetaArgs(
#         name="api",
#         namespace=namespace.metadata.name,
#     ),
#     spec=k8s.apps.v1.DeploymentSpecArgs(
#         selector=k8s.meta.v1.LabelSelectorArgs(
#             match_labels={"run": "api"},
#         ),
#         template=k8s.core.v1.PodTemplateSpecArgs(
#             metadata=k8s.meta.v1.ObjectMetaArgs(
#                 labels={"run": "api"},
#             ),
#             spec=k8s.core.v1.PodSpecArgs(
#                 volumes=[
#                     k8s.core.v1.VolumeArgs(
#                         name="persistent-vol",
#                         empty_dir=k8s.core.v1.EmptyDirVolumeSourceArgs(),
#                     ),
#                     k8s.core.v1.VolumeArgs(
#                         name="google-cloud-key",
#                         secret=k8s.core.v1.SecretVolumeSourceArgs(
#                             secret_name="gcp-service-key",
#                         ),
#                     ),
#                 ],
#                 containers=[
#                     k8s.core.v1.ContainerArgs(
#                         name="api",
#                         image=f"us-docker.pkg.dev/{project}/cheese-app-repository/cheese-app-api-service:{docker_tag}",
#                         image_pull_policy="IfNotPresent",
#                         ports=[k8s.core.v1.ContainerPortArgs(
#                             container_port=9000,
#                             protocol="TCP",
#                         )],
#                         volume_mounts=[
#                             k8s.core.v1.VolumeMountArgs(
#                                 name="persistent-vol",
#                                 mount_path="/persistent",
#                             ),
#                             k8s.core.v1.VolumeMountArgs(
#                                 name="google-cloud-key",
#                                 mount_path="/secrets",
#                             ),
#                         ],
#                         env=[
#                             k8s.core.v1.EnvVarArgs(
#                                 name="GOOGLE_APPLICATION_CREDENTIALS",
#                                 value="/secrets/gcp-service.json",
#                             ),
#                             k8s.core.v1.EnvVarArgs(
#                                 name="GCS_BUCKET_NAME",
#                                 value="cheese-app-models",
#                             ),
#                             k8s.core.v1.EnvVarArgs(
#                                 name="CHROMADB_HOST",
#                                 value="vector-db",
#                             ),
#                             k8s.core.v1.EnvVarArgs(
#                                 name="CHROMADB_PORT",
#                                 value="8000",
#                             ),
#                             k8s.core.v1.EnvVarArgs(
#                                 name="GCP_PROJECT",
#                                 value=project,
#                             ),
#                         ],
#                     ),
#                 ],
#             ),
#         ),
#     ),
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=api_deployment_deps),
# )

# # 8. Create Services

# # Frontend Service
# frontend_service = k8s.core.v1.Service(
#     "frontend-service",
#     metadata=k8s.meta.v1.ObjectMetaArgs(
#         name="frontend",
#         namespace=namespace.metadata.name,
#     ),
#     spec=k8s.core.v1.ServiceSpecArgs(
#         type="NodePort",
#         ports=[k8s.core.v1.ServicePortArgs(
#             port=3000,
#             target_port=3000,
#             protocol="TCP",
#         )],
#         selector={"run": "frontend"},
#     ),
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[frontend_deployment]),
# )

# # ChromaDB Service
# vector_db_service = k8s.core.v1.Service(
#     "vector-db-service",
#     metadata=k8s.meta.v1.ObjectMetaArgs(
#         name="vector-db",
#         namespace=namespace.metadata.name,
#     ),
#     spec=k8s.core.v1.ServiceSpecArgs(
#         type="NodePort",
#         ports=[k8s.core.v1.ServicePortArgs(
#             port=8000,
#             target_port=8000,
#             protocol="TCP",
#         )],
#         selector={"run": "vector-db"},
#     ),
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[vector_db_deployment]),
# )

# # API Service
# api_service = k8s.core.v1.Service(
#     "api-service",
#     metadata=k8s.meta.v1.ObjectMetaArgs(
#         name="api",
#         namespace=namespace.metadata.name,
#     ),
#     spec=k8s.core.v1.ServiceSpecArgs(
#         type="NodePort",
#         ports=[k8s.core.v1.ServicePortArgs(
#             port=9000,
#             target_port=9000,
#             protocol="TCP",
#         )],
#         selector={"run": "api"},
#     ),
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[api_deployment]),
# )

# # 9. Create Job for Loading Vector DB
# vector_db_loader_job = k8s.batch.v1.Job(
#     "vector-db-loader",
#     metadata=k8s.meta.v1.ObjectMetaArgs(
#         name="vector-db-loader",
#         namespace=namespace.metadata.name,
#     ),
#     spec=k8s.batch.v1.JobSpecArgs(
#         backoff_limit=4,
#         template=k8s.core.v1.PodTemplateSpecArgs(
#             spec=k8s.core.v1.PodSpecArgs(
#                 restart_policy="Never",
#                 init_containers=[
#                     k8s.core.v1.ContainerArgs(
#                         name="wait-for-chromadb",
#                         image="busybox:1.28",
#                         command=[
#                             "sh",
#                             "-c",
#                             'until wget --spider -S http://vector-db:8000/api/v1/heartbeat 2>&1 | grep "HTTP/1.1 200"; do echo "Waiting for ChromaDB..."; sleep 5; done;',
#                         ],
#                     ),
#                 ],
#                 containers=[
#                     k8s.core.v1.ContainerArgs(
#                         name="vector-db-loader",
#                         image=f"us-docker.pkg.dev/{project}/cheese-app-repository/cheese-app-vector-db-cli:{docker_tag}",
#                         env=[
#                             k8s.core.v1.EnvVarArgs(name="GCP_PROJECT", value=project),
#                             k8s.core.v1.EnvVarArgs(name="CHROMADB_HOST", value="vector-db"),
#                             k8s.core.v1.EnvVarArgs(name="CHROMADB_PORT", value="8000"),
#                             k8s.core.v1.EnvVarArgs(
#                                 name="GOOGLE_APPLICATION_CREDENTIALS",
#                                 value="/secrets/gcp-service.json",
#                             ),
#                         ],
#                         volume_mounts=[
#                             k8s.core.v1.VolumeMountArgs(
#                                 name="google-cloud-key",
#                                 mount_path="/secrets",
#                             ),
#                         ],
#                     ),
#                 ],
#                 volumes=[
#                     k8s.core.v1.VolumeArgs(
#                         name="google-cloud-key",
#                         secret=k8s.core.v1.SecretVolumeSourceArgs(
#                             secret_name="gcp-service-key",
#                         ),
#                     ),
#                 ],
#             ),
#         ),
#     ),
#     opts=pulumi.ResourceOptions(
#         provider=k8s_provider,
#         depends_on=[vector_db_service, api_deployment] if gcp_secret else [vector_db_service],
#     ),
# )

# # 10. Get nginx-ingress controller service to retrieve the external IP
# nginx_ingress_service = k8s.core.v1.Service.get(
#     "nginx-ingress-controller",
#     Output.concat(namespace.metadata.name, "/nginx-ingress-nginx-ingress"),
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[nginx_ingress]),
# )

# # Extract the LoadBalancer IP
# nginx_ingress_ip = nginx_ingress_service.status.apply(
#     lambda status: status.load_balancer.ingress[0].ip if status and status.load_balancer.ingress else None
# )

# # 11. Create Ingress Controller
# ingress = k8s.networking.v1.Ingress(
#     "ingress-resource",
#     metadata=k8s.meta.v1.ObjectMetaArgs(
#         name="ingress-resource",
#         namespace=namespace.metadata.name,
#         annotations={
#             "kubernetes.io/ingress.class": "nginx",
#             "nginx.ingress.kubernetes.io/ssl-redirect": "false",
#             "nginx.org/rewrites": "serviceName=frontend rewrite=/;serviceName=api rewrite=/",
#         },
#     ),
#     spec=k8s.networking.v1.IngressSpecArgs(
#         rules=[
#             k8s.networking.v1.IngressRuleArgs(
#                 host=nginx_ingress_ip.apply(lambda ip: f"{ip}.sslip.io" if ip else "pending.sslip.io"),
#                 http=k8s.networking.v1.HTTPIngressRuleValueArgs(
#                     paths=[
#                         k8s.networking.v1.HTTPIngressPathArgs(
#                             path="/",
#                             path_type="Prefix",
#                             backend=k8s.networking.v1.IngressBackendArgs(
#                                 service=k8s.networking.v1.IngressServiceBackendArgs(
#                                     name="frontend",
#                                     port=k8s.networking.v1.ServiceBackendPortArgs(number=3000),
#                                 ),
#                             ),
#                         ),
#                         k8s.networking.v1.HTTPIngressPathArgs(
#                             path="/api/",
#                             path_type="Prefix",
#                             backend=k8s.networking.v1.IngressBackendArgs(
#                                 service=k8s.networking.v1.IngressServiceBackendArgs(
#                                     name="api",
#                                     port=k8s.networking.v1.ServiceBackendPortArgs(number=9000),
#                                 ),
#                             ),
#                         ),
#                     ],
#                 ),
#             ),
#         ],
#     ),
#     opts=pulumi.ResourceOptions(
#         provider=k8s_provider,
#         depends_on=[frontend_service, api_service, nginx_ingress],
#     ),
# )

# # 12. Export outputs
# pulumi.export("cluster_name", cluster.name)
# pulumi.export("cluster_endpoint", cluster.endpoint)
# pulumi.export("kubeconfig", k8s_provider.kubeconfig)
# pulumi.export("namespace", namespace.metadata.name)
# pulumi.export("nginx_ingress_ip", nginx_ingress_ip)
# pulumi.export("application_url", nginx_ingress_ip.apply(lambda ip: f"http://{ip}.sslip.io" if ip else "pending"))






































import pulumi
import pulumi_gcp as gcp
from pulumi import StackReference, ResourceOptions, Output
import pulumi_kubernetes as k8s

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
gcp_config = pulumi.Config("gcp")
project = gcp_config.get("project")
region = gcp_config.get("region")
base_config = pulumi.Config()
cluster_name = base_config.get("clusterName")
description = base_config.get("description")
initial_node_count = base_config.get_int("initialNodeCount")
machine_type = base_config.get("machineType") 
machine_disk_size = base_config.get_int("machineDiskSize")
service_account_email = pulumi.Config("security").get("gcp_service_account_email")
ksa_service_account_email = pulumi.Config("security").get("gcp_ksa_service_account_email")  

# Get image references from deploy_images stack
# For local backend, use: "organization/project/stack"
images_stack = pulumi.StackReference("organization/deploy-images/dev")
# Get the image tags (these are arrays, so we take the first element)
api_service_tag = images_stack.get_output("cheese-app-api-service-tags")
frontend_tag = images_stack.get_output("cheese-app-frontend-react-tags")
vector_db_cli_tag = images_stack.get_output("cheese-app-vector-db-cli-tags")



# -----------------------------------------------------------------------------
# Network & Subnet
# -----------------------------------------------------------------------------

# Create VPC network with manual subnet configuration for the cheese app
network = gcp.compute.Network(
    "cheese-app-vpc",
    name="cheese-app-vpc-test",
    auto_create_subnetworks=False,
    routing_mode="REGIONAL",
    description="VPC for Cheese App Kubernetes Cluster",
)



# Create subnet within the VPC with private Google access enabled
subnet = gcp.compute.Subnetwork(
    "cheese-app-subnet-test",
    name="cheese-app-subnet-test",
    ip_cidr_range="10.0.0.0/19",
    region=region,
    network=network.id,
    private_ip_google_access=True,
    description="subnet /19 starting after 10.0.0.0/19",
    opts=pulumi.ResourceOptions(depends_on=[network])

)


# Create Cloud Router to enable NAT for private instances
router = gcp.compute.Router(
    "cheese-app-router-test",
    name="cheese-app-router-test",
    network=network.id,
    region=region,
    opts=pulumi.ResourceOptions(depends_on=[network,subnet])
)

# Configure Cloud NAT to allow private instances to access the internet
nat = gcp.compute.RouterNat(
    "cheese-app-nat-test",
    name="cheese-app-nat-test",
    router=router.name,
    region=region,
    nat_ip_allocate_option="AUTO_ONLY",
    source_subnetwork_ip_ranges_to_nat="ALL_SUBNETWORKS_ALL_IP_RANGES",
    log_config=gcp.compute.RouterNatLogConfigArgs(enable=True, filter="ERRORS_ONLY"),
    opts=pulumi.ResourceOptions(depends_on=[router])

)


# -----------------------------
# Cluster (private, no default pool)
# -----------------------------
# Create GKE cluster with private nodes, workload identity enabled, and no default node pool
cluster = gcp.container.Cluster(
    "dev_cluster-test",
    name=cluster_name,
    description=description,
    location=region,
    deletion_protection=False,
    network=network.name,
    subnetwork=subnet.name,
    remove_default_node_pool=True,  # Remove default pool to use custom node pools
    initial_node_count=1,
    private_cluster_config={
        "enable_private_nodes": True,  # Nodes use private IPs only
        "enable_private_endpoint": False,  # Control plane accessible via public endpoint
        "master_ipv4_cidr_block": "172.0.0.0/28",  # CIDR for GKE control plane
    },
    workload_identity_config={"workload_pool": f"{project}.svc.id.goog"},  # Enable Workload Identity for secure service account access
    gateway_api_config={
        "channel": "CHANNEL_STANDARD",  # Enable Gateway API for advanced ingress
    },
)


# -----------------------------
# Node Pool (standard nodes)
# -----------------------------
# Create custom node pool with autoscaling, auto-repair, and standard GCP service permissions
node_pool = gcp.container.NodePool(
    "default-pool-test",
    cluster=cluster.name,
    location=region,
    initial_node_count=1,
    node_config=gcp.container.NodePoolNodeConfigArgs(
        service_account=service_account_email,
        machine_type=machine_type,
        image_type="cos_containerd",  # Container-Optimized OS with containerd runtime
        disk_size_gb=machine_disk_size,
        oauth_scopes=[  # OAuth scopes for node service account permissions
            "https://www.googleapis.com/auth/devstorage.read_only",  # Read from GCS
            "https://www.googleapis.com/auth/logging.write",  # Write logs to Cloud Logging
            "https://www.googleapis.com/auth/monitoring",  # Send metrics to Cloud Monitoring
            "https://www.googleapis.com/auth/servicecontrol",  # Service control access
            "https://www.googleapis.com/auth/service.management.readonly",  # Read service management
            "https://www.googleapis.com/auth/trace.append",  # Write traces to Cloud Trace
        ],
    ),
    autoscaling=gcp.container.NodePoolAutoscalingArgs(
        min_node_count=1,  # Minimum nodes to keep running
        max_node_count=2,  # Maximum nodes for scale-up
    ),
    management=gcp.container.NodePoolManagementArgs(
        auto_repair=True,  # Automatically repair unhealthy nodes
        auto_upgrade=True,  # Automatically upgrade to new GKE versions
    ),
    node_locations=['us-central1-a']
)

# -----------------------------
# Kubeconfig for k8s provider
# -----------------------------
k8s_info = pulumi.Output.all(cluster.name, cluster.endpoint, cluster.master_auth)
cluster_kubeconfig = k8s_info.apply(
    lambda info: f"""apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {info[2]["cluster_ca_certificate"]}
    server: https://{info[1]}
  name: {project}_{region}_{info[0]}
contexts:
- context:
    cluster: {project}_{region}_{info[0]}
    user: {project}_{region}_{info[0]}
  name: {project}_{region}_{info[0]}
current-context: {project}_{region}_{info[0]}
kind: Config
preferences: {{}}
users:
- name: {project}_{region}_{info[0]}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gke-gcloud-auth-plugin
      installHint: Install gke-gcloud-auth-plugin for use with kubectl
      provideClusterInfo: true
      interactiveMode: Never
"""
)

# -----------------------------
# Create K8s Provider
# -----------------------------

# Create Kubernetes provider using GKE cluster credentials to deploy K8s resources
k8s_provider = k8s.Provider(
    "gke_k8s",
    kubeconfig=cluster_kubeconfig,  # Use the kubeconfig generated from the GKE cluster
    opts=ResourceOptions(depends_on=[node_pool]),  # Wait for node pool to be ready
)

# -----------------------------
# Create Namespaces and KSA
# -----------------------------

# Create Kubernetes namespace for application deployments
namespace = k8s.core.v1.Namespace(
    "deployments-namespace-test",
    metadata={"name": "deployments-test"},
    opts=ResourceOptions(provider=k8s_provider),
)

# --- Kubernetes Service Account (KSA) with Workload Identity annotation ---
# KSA = Kubernetes Service Account - an identity used by pods running in K8s to authenticate
# This allows pods to securely access GCP services without embedding credentials
ksa_name = "api-ksa"
api_ksa = k8s.core.v1.ServiceAccount(
    "api-ksa",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name=ksa_name,
        namespace=namespace.metadata["name"],
        annotations={
            # Critical: map KSA → GSA (Google Service Account) for Workload Identity
            "iam.gke.io/gcp-service-account": f"{ksa_service_account_email}",
        },
    ),
    opts=ResourceOptions(provider=k8s_provider),
)

# --- Bind KSA identity to the GSA (Workload Identity user) ---
# This IAM binding allows the KSA to impersonate the GSA and use its GCP permissions
# member format: serviceAccount:<PROJECT_ID>.svc.id.goog[<namespace>/<ksa_name>]
project_id = gcp.config.project
wi_member = Output.concat(  # Build the Workload Identity member string
    "serviceAccount:",
    project_id,
    ".svc.id.goog[",
    namespace.metadata["name"],
    "/",
    ksa_name,
    "]",
)

# Construct the full GSA resource ID
gsa_full_id = pulumi.Output.concat(
    "projects/", project_id, "/serviceAccounts/", f"{ksa_service_account_email}"
)
# Grant the KSA permission to act as the GSA
gsa_wi_binding_strict = gcp.serviceaccount.IAMMember(
    "api-gsa-wi-user-test",
    service_account_id=gsa_full_id,
    role="roles/iam.workloadIdentityUser",  # Required role for Workload Identity
    member=wi_member,  # The KSA that will impersonate this GSA
)


# --- Create Persistent Volume Claims (PVCs) for stateful storage ---
# PVCs request persistent storage from the cluster that survives pod restarts

# General persistent storage for application data (5Gi)
persistent_pvc = k8s.core.v1.PersistentVolumeClaim(
    "persistent-pvc-test",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="persistent-pvc-test",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
        access_modes=["ReadWriteOnce"],  # Single pod read/write access
        resources=k8s.core.v1.VolumeResourceRequirementsArgs(
            requests={"storage": "5Gi"},  # Request 5GB of persistent storage
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
)


# Dedicated storage for ChromaDB vector database (10Gi)
chromadb_pvc = k8s.core.v1.PersistentVolumeClaim(
    "chromadb-pvc-test",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="chromadb-pvc-test",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
        access_modes=["ReadWriteOnce"],  # Single pod read/write access
        resources=k8s.core.v1.VolumeResourceRequirementsArgs(
            requests={"storage": "10Gi"},  # Request 10GB for vector embeddings
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
)



# # --------------------------
# # Pod Deployments & Services
# # --------------------------

# --- Frontend Deployment ---
# Creates pods running the frontend container on port 3000
# ram 1.7 gb
frontend_deployment = k8s.apps.v1.Deployment(
    "frontend-test",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="frontend-test",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.apps.v1.DeploymentSpecArgs(
        selector=k8s.meta.v1.LabelSelectorArgs(
            match_labels={"run": "frontend-test"},  # Select pods with this label
        ),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(
                labels={"run": "frontend-test"},  # Label assigned to pods
            ),
            spec=k8s.core.v1.PodSpecArgs(
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="frontend-test",
                        image=frontend_tag.apply(lambda tags: tags[0]),  # Container image (placeholder - needs to be filled)
                        image_pull_policy="IfNotPresent",  # Use cached image if available
                        ports=[k8s.core.v1.ContainerPortArgs(
                            container_port=3000,  # Frontend app listens on port 3000
                            protocol="TCP",
                        )],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"cpu": "250m", "memory": "2Gi"},
                            limits={"cpu": "500m", "memory": "3Gi"},
                        ),
                    ),
                ],
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
)


# --- Frontend Service ---
# ClusterIP service for internal cluster access to frontend pods
# Cluster URL: http://frontend.deployments.svc.cluster.local:3000
# Format: http://<service-name>.<namespace>.svc.cluster.local:<port>
#
# Service Type Comparison:
# ├──────────────┬──────────────┬─────────────┬────────────────────────────────┤
# │ Type         │ External IP  │ Ports       │ Use Case                       │
# ├──────────────┼──────────────┼─────────────┼────────────────────────────────┤
# │ ClusterIP    │ No           │ Any         │ Internal services only         │
# │ NodePort     │ Yes (manual) │ 30000-32767 │ Dev/testing, direct access     │
# │ LoadBalancer │ Yes (auto)   │ Any         │ Production, HA, auto-scaling   │
# └──────────────┴──────────────┴─────────────┴────────────────────────────────┘
frontend_service = k8s.core.v1.Service(
    "frontend-service-test",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="frontend-test",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.ServiceSpecArgs(
        type="ClusterIP",  # Internal only - not exposed outside cluster
        ports=[k8s.core.v1.ServicePortArgs(
            port=3000,  # Service port
            target_port=3000,  # Container port to forward to
            protocol="TCP",
        )],
        selector={"run": "frontend-test"},  # Route traffic to pods with this label
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[frontend_deployment]),
)



    # ----- BackendConfig (LB health check -> /api/health) -----
# frontend_backendcfg = k8s.apiextensions.CustomResource(
#     f"frontend-backendconfig",
#     api_version="cloud.google.com/v1",
#     kind="BackendConfig",
#     metadata={"name": "frontend-backendconfig", "namespace": namespace.metadata.name},
#     spec={
#         "healthCheck": {
#             "type": "HTTP",
#             "requestPath": "/",
#             "port": 3000,
#             "checkIntervalSec": 5,
#             "timeoutSec": 5,
#         }
#     },
#     opts=ResourceOptions(provider=k8s_provider),
# )



# --- ChromaDB Deployment ---
# Vector database for storing embeddings with persistent storage
vector_db_deployment = k8s.apps.v1.Deployment(
    "vector-db-test",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="vector-db-test",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.apps.v1.DeploymentSpecArgs(
        selector=k8s.meta.v1.LabelSelectorArgs(
            match_labels={"run": "vector-db-test"},
        ),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(
                labels={"run": "vector-db-test"},
            ),
            spec=k8s.core.v1.PodSpecArgs(
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="vector-db-test",
                        image="chromadb/chroma:0.5.6",  # ChromaDB vector database
                        ports=[k8s.core.v1.ContainerPortArgs(
                            container_port=8000,  # ChromaDB API port
                            protocol="TCP",
                        )],
                        env=[
                            k8s.core.v1.EnvVarArgs(name="IS_PERSISTENT", value="TRUE"),  # Enable data persistence
                            k8s.core.v1.EnvVarArgs(name="ANONYMIZED_TELEMETRY", value="FALSE"),  # Disable telemetry
                        ],
                        volume_mounts=[
                            k8s.core.v1.VolumeMountArgs(
                                name="chromadb-storage-test",
                                mount_path="/chroma/chroma",  # ChromaDB data directory
                            ),
                        ],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"cpu": "100m", "memory": "128Mi"},
                            limits={"cpu": "200m", "memory": "256Mi"},
                        ),
                    ),
                ],
                volumes=[
                    k8s.core.v1.VolumeArgs(
                        name="chromadb-storage-test",
                        persistent_volume_claim=k8s.core.v1.PersistentVolumeClaimVolumeSourceArgs(
                            claim_name=chromadb_pvc.metadata.name,
                            # Mount the 10Gi PVC
                        ),
                    ),
                ],
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace, chromadb_pvc]),
)



# ChromaDB service for internal cluster access
# Cluster URL: http://vector-db.deployments.svc.cluster.local:8000
vector_db_service = k8s.core.v1.Service(
    "vector-db-service-test",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="vector-db-test",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.ServiceSpecArgs(
        type="ClusterIP",  # Internal only
        ports=[k8s.core.v1.ServicePortArgs(
            port=8000,
            target_port=8000,
            protocol="TCP",
        )],
        selector={"run": "vector-db-test"},
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[vector_db_deployment]),
)


# --- Vector DB Loader Job ---
# One-time job to populate ChromaDB with initial embeddings/data
# Jobs run to completion and don't restart (unlike Deployments)
# ram 200mb
vector_db_loader_job = k8s.batch.v1.Job(
    "vector-db-loader",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="vector-db-loader",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.batch.v1.JobSpecArgs(
        backoff_limit=4,  # Retry up to 4 times on failure
        template=k8s.core.v1.PodTemplateSpecArgs(
            spec=k8s.core.v1.PodSpecArgs(
                service_account_name=ksa_name,  # Use Workload Identity for GCP access
                security_context=k8s.core.v1.PodSecurityContextArgs(
                        fs_group=1000,
                    ),
                restart_policy="Never",  # Don't restart pod on completion
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="vector-db-loader",
                        image=vector_db_cli_tag.apply(lambda tags: tags[0]),  # Loader image (placeholder - needs to be filled)
                        env=[
                            k8s.core.v1.EnvVarArgs(name="GCP_PROJECT", value=project),
                            k8s.core.v1.EnvVarArgs(name="CHROMADB_HOST", value="vector-db-test"),  # Connect to ChromaDB service
                            k8s.core.v1.EnvVarArgs(name="CHROMADB_PORT", value="8000"),
                        ],
                        command=[
                            "cli.py",
                            "--download",
                            "--load",
                            "--chunk_type",
                            "recursive-split",
                        ],

                    ),
                ]
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[vector_db_service],  # Run after services are ready
    ),
)


# --- API Deployment ---
# Backend API with Workload Identity for GCS/GCP access and ChromaDB integration

# ram 300 mb 
api_deployment = k8s.apps.v1.Deployment(
    "api",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="api",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.apps.v1.DeploymentSpecArgs(
        selector=k8s.meta.v1.LabelSelectorArgs(
            match_labels={"run": "api"},
        ),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(
                labels={"run": "api"},
            ),
            spec=k8s.core.v1.PodSpecArgs(
                service_account_name=ksa_name,  # Use KSA for Workload Identity (GCP access)
                security_context=k8s.core.v1.PodSecurityContextArgs(
                        fs_group=1000,
                    ),
                volumes=[
                    k8s.core.v1.VolumeArgs(
                        name="persistent-vol",
                        persistent_volume_claim=k8s.core.v1.PersistentVolumeClaimVolumeSourceArgs(
                            claim_name=persistent_pvc.metadata.name,  # Temporary storage (lost on restart)
                        ),
                    )
                ],
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="api",
                        image=api_service_tag.apply(lambda tags: tags[0]),  # API container image (placeholder - needs to be filled)
                        image_pull_policy="IfNotPresent",
                        ports=[k8s.core.v1.ContainerPortArgs(
                            container_port=9000,  # API server port
                            protocol="TCP",
                        )],
                        volume_mounts=[
                            k8s.core.v1.VolumeMountArgs(
                                name="persistent-vol",
                                mount_path="/persistent",  # Temporary file storage
                            )
                        ],
                        env=[
                            k8s.core.v1.EnvVarArgs(
                                name="GCS_BUCKET_NAME",
                                value="cheese-app-models",  # GCS bucket for ML models
                            ),
                            k8s.core.v1.EnvVarArgs(
                                name="CHROMADB_HOST",
                                value="vector-db-test",  # ChromaDB service name (DNS)
                            ),
                            k8s.core.v1.EnvVarArgs(
                                name="CHROMADB_PORT",
                                value="8000",
                            ),
                            k8s.core.v1.EnvVarArgs(
                                name="GCP_PROJECT",
                                value=project,
                            ),
                        ],
                    ),
                ],
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[vector_db_loader_job]),
)



# API service for internal cluster access
# Cluster URL: http://api.deployments.svc.cluster.local:9000
api_service = k8s.core.v1.Service(
    "api-service",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="api",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.ServiceSpecArgs(
        type="ClusterIP",  # Internal only
        ports=[k8s.core.v1.ServicePortArgs(
            port=9000,
            target_port=9000,
            protocol="TCP",
        )],
        selector={"run": "api"},
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[api_deployment]),
)


# -----------------------------------------------------------------------------
# Install Cert-Manager for Automatic TLS Certificates
# -----------------------------------------------------------------------------
# cert_manager = k8s.helm.v3.Release(
#     "cert-manager",
#     chart="cert-manager",
#     namespace=namespace.metadata.name,
#     version="v1.14.1",
#     repository_opts=k8s.helm.v3.RepositoryOptsArgs(
#         repo="https://charts.jetstack.io"
#     ),
#     values={"installCRDs": True},
#     opts=ResourceOptions(provider=k8s_provider),
# )

# # Create a ClusterIssuer for Let's Encrypt
# letsencrypt_issuer = k8s.apiextensions.CustomResource(
#     "letsencrypt-clusterissuer",
#     api_version="cert-manager.io/v1",
#     kind="ClusterIssuer",
#     metadata={"name": "letsencrypt-prod"},
#     spec={
#         "acme": {
#             "email": "karthikmrathod1999@gmail.com",  # Update with your email
#             "server": "https://acme-v02.api.letsencrypt.org/directory",
#             "privateKeySecretRef": {"name": "letsencrypt-prod"},
#             "solvers": [{"http01": {"ingress": {"class": "nginx"}}}],
#         }
#     },
#     opts=ResourceOptions(provider=k8s_provider, depends_on=[cert_manager]),
# )

# # -----------------------------------------------------------------------------
# # Deploy Nginx Ingress Controller using Helm and Create Ingress Resource
# # -----------------------------------------------------------------------------

# # Deploy the Nginx Ingress Controller via the Bitnami Helm chart.
# nginx_helm = k8s.helm.v3.Release(
#     "nginx-helm",
#     chart="nginx-ingress-controller",
#     namespace=namespace.metadata.name,
#     repository_opts=k8s.helm.v3.RepositoryOptsArgs(
#         repo="https://charts.bitnami.com/bitnami"
#     ),
#     values={
#         "service": {
#             "type": "LoadBalancer",
#         },
#         "resources": {
#             "requests": {"memory": "128Mi", "cpu": "100m"},
#             "limits": {"memory": "256Mi", "cpu": "200m"},
#         },
#         "replicaCount": 1,
#         "ingressClassResource": {"name": "nginx", "enabled": True, "default": True},
#         "config": {"use-forwarded-headers": "true"},
#     },
#     opts=ResourceOptions(provider=k8s_provider),
# )

# # Get the service created by Helm to extract the LoadBalancer IP
# nginx_service = k8s.core.v1.Service.get(
#     "nginx-ingress-service",
#     pulumi.Output.concat(
#         nginx_helm.status.namespace,
#         "/",
#         nginx_helm.status.name,
#         "-nginx-ingress-controller"  # often resolves to <release-name>-ingress-nginx-controller
#     ),
#     opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[nginx_helm]),
# )
# nginx_ingress_ip = nginx_service.status.load_balancer.ingress[0].ip
# host = nginx_ingress_ip.apply(lambda ip: f"{ip}.sslip.io")
# # -----------------------------------------------------------------------------
# #Ingress to use TLS
# # -----------------------------------------------------------------------------
# ingress = k8s.networking.v1.Ingress(
#     "nginx-ingress-test",
#     metadata=k8s.meta.v1.ObjectMetaArgs(
#         name="nginx-ingress-test",
#         namespace=namespace.metadata.name,
#         annotations={
                # "nginx.ingress.kubernetes.io/ssl-redirect": "true",
                # "cert-manager.io/cluster-issuer": "letsencrypt-prod",
                # "nginx.ingress.kubernetes.io/use-regex": "true",

#         },
#     ),
#     spec=k8s.networking.v1.IngressSpecArgs(
#         # IMPORTANT: matches controller.ingressClass.name from the Helm values
#         ingress_class_name="nginx",
#         tls=[
#             k8s.networking.v1.IngressTLSArgs(
#                 hosts=[host], # your domain here
#                 secret_name="temp-instel-tls", # this name can be anything you want 
#             )
#         ],
#         rules=[
#             k8s.networking.v1.IngressRuleArgs(
#                 host=host, # your domain here
#                 http=k8s.networking.v1.HTTPIngressRuleValueArgs(
#                     paths=[
#                         # API service – no regex, no rewrite
#                         # k8s.networking.v1.HTTPIngressPathArgs(
#                         #     path="/api-service",
#                         #     path_type="Prefix",
#                         #     backend=k8s.networking.v1.IngressBackendArgs(
#                         #         service=k8s.networking.v1.IngressServiceBackendArgs(
#                         #             name=api_service.metadata["name"],
#                         #             port=k8s.networking.v1.ServiceBackendPortArgs(
#                         #                 number=9000
#                         #             ),
#                         #         )
#                         #     ),
#                         # ),
#                         # Frontend
#                         k8s.networking.v1.HTTPIngressPathArgs(
#                             path="/",
#                             path_type="Prefix",
#                             backend=k8s.networking.v1.IngressBackendArgs(
#                                 service=k8s.networking.v1.IngressServiceBackendArgs(
#                                     name=frontend_service.metadata["name"],
#                                     port=k8s.networking.v1.ServiceBackendPortArgs(
#                                         number=3000
#                                     ),
#                                 )
#                             ),
#                         ),
#                     ]
#                 ),
#             )
#         ],
#     ),
#     opts=ResourceOptions(
#         provider=k8s_provider,
#         depends_on=[nginx_helm, letsencrypt_issuer],
#     ),
# )

global_ip = gcp.compute.GlobalAddress(
    "global-static-ip",
    name="cheese-app-global-ip-test",
    address_type="EXTERNAL",
    ip_version="IPV4",
)

host = global_ip.address.apply(lambda ip: f"{ip}.sslip.io")
managed_cert = k8s.apiextensions.CustomResource(
        "managed-cert",  # <-- static logical name
        api_version="networking.gke.io/v1beta1",
        kind="ManagedCertificate",
        metadata={
            "name": "managed-certificates",          # <-- dynamic via Output
            "namespace": namespace.metadata.name,     # <-- Output[str] is fine
        },
        spec={"domains": [host]},
        opts=ResourceOptions(provider=k8s_provider,depends_on=[global_ip]),
    )

frontend_cfg = k8s.apiextensions.CustomResource(
    "https-redirect",  # <-- static logical name
    api_version="networking.gke.io/v1beta1",
    kind="FrontendConfig",
    metadata={
        "name": "https-redirect",
        "namespace": namespace.metadata.name,
    },
    spec={"redirectToHttps": {"enabled": True}},
    opts=ResourceOptions(provider=k8s_provider),
)

# Ingress (GCE, NEG backend, managed certs)
ingress = k8s.networking.v1.Ingress(
    "ac215-ingress",  # <-- static logical name
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="ac215-ingress-new",
        namespace=namespace.metadata.name,
        annotations={
            "kubernetes.io/ingress.class": "gce",
            # NAME of Global Static IP (plain str from config is OK)
            "kubernetes.io/ingress.global-static-ip-name": global_ip.name,
            # These must match the dynamic metadata.name values above
            "networking.gke.io/managed-certificates": "managed-certificates",
            "networking.gke.io/frontend-config": "https-redirect",
            
        },
    ),
    spec=k8s.networking.v1.IngressSpecArgs(
        # No spec.tls when using Google-managed certificates
        rules=[
            k8s.networking.v1.IngressRuleArgs(
                host=host,
                http=k8s.networking.v1.HTTPIngressRuleValueArgs(
                    paths=[
                        k8s.networking.v1.HTTPIngressPathArgs(
                            path="/",
                            path_type="Prefix",
                            backend=k8s.networking.v1.IngressBackendArgs(
                                service=k8s.networking.v1.IngressServiceBackendArgs(
                                    name=frontend_service.metadata.name,  # Output[str] is fine
                                    port=k8s.networking.v1.ServiceBackendPortArgs(
                                        number=3000,      # Output[int] is fine
                                    ),
                                )
                            ),
                        ),
                        k8s.networking.v1.HTTPIngressPathArgs(
                            path="/api-service",
                            path_type="Prefix",
                            backend=k8s.networking.v1.IngressBackendArgs(
                                service=k8s.networking.v1.IngressServiceBackendArgs(
                                    name=api_service.metadata.name,  # Output[str] is fine
                                    port=k8s.networking.v1.ServiceBackendPortArgs(
                                        number=9000,      # Output[int] is fine
                                    ),
                                )
                            ),
                        )
                        
                    ]
                ),
            )
        ],
    ),
    opts=ResourceOptions(
        provider=k8s_provider,
        depends_on=[managed_cert, frontend_cfg],
    ),
)




pulumi.export("cluster_name", cluster.name)
pulumi.export("cluster_endpoint", cluster.endpoint)
pulumi.export("kubeconfig", k8s_provider.kubeconfig)
pulumi.export("namespace", namespace.metadata.name)
pulumi.export("application_url", "https://temp.instel.ai")  # your domain
# pulumi.export("ingress_name", ingress.metadata.name)
# pulumi.export("nginx_ingress_ip", nginx_ingress_ip)
