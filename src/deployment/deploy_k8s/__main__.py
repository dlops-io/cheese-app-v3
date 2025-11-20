import pulumi
import pulumi_gcp as gcp
import pulumi_kubernetes as k8s
from pulumi import StackReference, ResourceOptions, Output

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

security_config = pulumi.Config("security")
service_account_email = security_config.get("gcp_service_account_email")
ksa_service_account_email = security_config.get("gcp_ksa_service_account_email")

# Get image references from deploy_images stack
images_stack = StackReference("organization/deploy-images/dev")
api_service_tag = images_stack.get_output("cheese-app-api-service-tags")
frontend_tag = images_stack.get_output("cheese-app-frontend-react-tags")
vector_db_cli_tag = images_stack.get_output("cheese-app-vector-db-cli-tags")

# -----------------------------------------------------------------------------
# Network & Subnet
# -----------------------------------------------------------------------------
network = gcp.compute.Network(
    "cheese-app-vpc",
    name="cheese-app-vpc-test",
    auto_create_subnetworks=False,
    routing_mode="REGIONAL",
    description="VPC for Cheese App Kubernetes Cluster",
)

subnet = gcp.compute.Subnetwork(
    "cheese-app-subnet-test",
    name="cheese-app-subnet-test",
    ip_cidr_range="10.0.0.0/19",
    region=region,
    network=network.id,
    private_ip_google_access=True,
    description="Subnet /19 starting at 10.0.0.0/19",
    opts=ResourceOptions(depends_on=[network]),
)

router = gcp.compute.Router(
    "cheese-app-router-test",
    name="cheese-app-router-test",
    network=network.id,
    region=region,
    opts=ResourceOptions(depends_on=[network, subnet]),
)

nat = gcp.compute.RouterNat(
    "cheese-app-nat-test",
    name="cheese-app-nat-test",
    router=router.name,
    region=region,
    nat_ip_allocate_option="AUTO_ONLY",
    source_subnetwork_ip_ranges_to_nat="ALL_SUBNETWORKS_ALL_IP_RANGES",
    log_config=gcp.compute.RouterNatLogConfigArgs(
        enable=True,
        filter="ERRORS_ONLY",
    ),
    opts=ResourceOptions(depends_on=[router]),
)

# -----------------------------------------------------------------------------
# GKE Cluster & Node Pool
# -----------------------------------------------------------------------------
cluster = gcp.container.Cluster(
    "dev_cluster-test",
    name=cluster_name,
    description=description,
    location=region,
    deletion_protection=False,
    network=network.name,
    subnetwork=subnet.name,
    remove_default_node_pool=True,
    initial_node_count=1,
    private_cluster_config={
        "enable_private_nodes": True,
        "enable_private_endpoint": False,
        "master_ipv4_cidr_block": "172.0.0.0/28",
    },
    workload_identity_config={
        "workload_pool": f"{project}.svc.id.goog",
    },
    gateway_api_config={
        "channel": "CHANNEL_STANDARD",
    },
)

node_pool = gcp.container.NodePool(
    "default-pool-test",
    cluster=cluster.name,
    location=region,
    initial_node_count=initial_node_count or 1,
    node_config=gcp.container.NodePoolNodeConfigArgs(
        service_account=service_account_email,
        machine_type=machine_type,
        image_type="cos_containerd",
        disk_size_gb=machine_disk_size,
        oauth_scopes=[
            "https://www.googleapis.com/auth/devstorage.read_only",
            "https://www.googleapis.com/auth/logging.write",
            "https://www.googleapis.com/auth/monitoring",
            "https://www.googleapis.com/auth/servicecontrol",
            "https://www.googleapis.com/auth/service.management.readonly",
            "https://www.googleapis.com/auth/trace.append",
        ],
    ),
    autoscaling=gcp.container.NodePoolAutoscalingArgs(
        min_node_count=1,
        max_node_count=2,
    ),
    management=gcp.container.NodePoolManagementArgs(
        auto_repair=True,
        auto_upgrade=True,
    ),
    node_locations=["us-central1-a"],
)

# -----------------------------------------------------------------------------
# Kubeconfig & Kubernetes Provider
# -----------------------------------------------------------------------------
k8s_info = Output.all(cluster.name, cluster.endpoint, cluster.master_auth)

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

k8s_provider = k8s.Provider(
    "gke_k8s",
    kubeconfig=cluster_kubeconfig,
    opts=ResourceOptions(depends_on=[node_pool]),
)

# -----------------------------------------------------------------------------
# Namespace & Service Accounts (Workload Identity)
# -----------------------------------------------------------------------------
namespace = k8s.core.v1.Namespace(
    "deployments-namespace-test",
    metadata={"name": "deployments-test"},
    opts=ResourceOptions(provider=k8s_provider),
)

ksa_name = "api-ksa"
api_ksa = k8s.core.v1.ServiceAccount(
    "api-ksa",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name=ksa_name,
        namespace=namespace.metadata["name"],
        annotations={
            "iam.gke.io/gcp-service-account": ksa_service_account_email,
        },
    ),
    opts=ResourceOptions(provider=k8s_provider),
)

project_id = gcp.config.project

wi_member = Output.concat(
    "serviceAccount:",
    project_id,
    ".svc.id.goog[",
    namespace.metadata["name"],
    "/",
    ksa_name,
    "]",
)

gsa_full_id = Output.concat(
    "projects/", project_id, "/serviceAccounts/", ksa_service_account_email
)

gsa_wi_binding_strict = gcp.serviceaccount.IAMMember(
    "api-gsa-wi-user-test",
    service_account_id=gsa_full_id,
    role="roles/iam.workloadIdentityUser",
    member=wi_member,
)

# -----------------------------------------------------------------------------
# Persistent Volume Claims
# -----------------------------------------------------------------------------
persistent_pvc = k8s.core.v1.PersistentVolumeClaim(
    "persistent-pvc-test",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="persistent-pvc-test",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
        access_modes=["ReadWriteOnce"],
        resources=k8s.core.v1.VolumeResourceRequirementsArgs(
            requests={"storage": "5Gi"},
        ),
    ),
    opts=ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
)

chromadb_pvc = k8s.core.v1.PersistentVolumeClaim(
    "chromadb-pvc-test",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="chromadb-pvc-test",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
        access_modes=["ReadWriteOnce"],
        resources=k8s.core.v1.VolumeResourceRequirementsArgs(
            requests={"storage": "10Gi"},
        ),
    ),
    opts=ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
)

# -----------------------------------------------------------------------------
# Frontend Deployment & Service
# -----------------------------------------------------------------------------
frontend_deployment = k8s.apps.v1.Deployment(
    "frontend-test",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="frontend-test",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.apps.v1.DeploymentSpecArgs(
        selector=k8s.meta.v1.LabelSelectorArgs(
            match_labels={"run": "frontend-test"},
        ),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(
                labels={"run": "frontend-test"},
            ),
            spec=k8s.core.v1.PodSpecArgs(
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="frontend-test",
                        image=frontend_tag.apply(lambda tags: tags[0]),
                        image_pull_policy="IfNotPresent",
                        ports=[
                            k8s.core.v1.ContainerPortArgs(
                                container_port=3000,
                                protocol="TCP",
                            )
                        ],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"cpu": "250m", "memory": "2Gi"},
                            limits={"cpu": "500m", "memory": "3Gi"},
                        ),
                    )
                ],
            ),
        ),
    ),
    opts=ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
)

frontend_service = k8s.core.v1.Service(
    "frontend-service-test",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="frontend-test",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.ServiceSpecArgs(
        type="ClusterIP",
        ports=[
            k8s.core.v1.ServicePortArgs(
                port=3000,
                target_port=3000,
                protocol="TCP",
            )
        ],
        selector={"run": "frontend-test"},
    ),
    opts=ResourceOptions(provider=k8s_provider, depends_on=[frontend_deployment]),
)

# -----------------------------------------------------------------------------
# ChromaDB Deployment & Service
# -----------------------------------------------------------------------------
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
                        image="chromadb/chroma:0.5.6",
                        ports=[
                            k8s.core.v1.ContainerPortArgs(
                                container_port=8000,
                                protocol="TCP",
                            )
                        ],
                        env=[
                            k8s.core.v1.EnvVarArgs(
                                name="IS_PERSISTENT", value="TRUE"
                            ),
                            k8s.core.v1.EnvVarArgs(
                                name="ANONYMIZED_TELEMETRY", value="FALSE"
                            ),
                        ],
                        volume_mounts=[
                            k8s.core.v1.VolumeMountArgs(
                                name="chromadb-storage-test",
                                mount_path="/chroma/chroma",
                            )
                        ],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"cpu": "100m", "memory": "128Mi"},
                            limits={"cpu": "200m", "memory": "256Mi"},
                        ),
                    )
                ],
                volumes=[
                    k8s.core.v1.VolumeArgs(
                        name="chromadb-storage-test",
                        persistent_volume_claim=k8s.core.v1.PersistentVolumeClaimVolumeSourceArgs(
                            claim_name=chromadb_pvc.metadata.name,
                        ),
                    )
                ],
            ),
        ),
    ),
    opts=ResourceOptions(
        provider=k8s_provider, depends_on=[namespace, chromadb_pvc]
    ),
)

vector_db_service = k8s.core.v1.Service(
    "vector-db-service-test",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="vector-db-test",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.ServiceSpecArgs(
        type="ClusterIP",
        ports=[
            k8s.core.v1.ServicePortArgs(
                port=8000,
                target_port=8000,
                protocol="TCP",
            )
        ],
        selector={"run": "vector-db-test"},
    ),
    opts=ResourceOptions(
        provider=k8s_provider, depends_on=[vector_db_deployment]
    ),
)

# -----------------------------------------------------------------------------
# Vector DB Loader Job
# -----------------------------------------------------------------------------
vector_db_loader_job = k8s.batch.v1.Job(
    "vector-db-loader",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="vector-db-loader-test",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.batch.v1.JobSpecArgs(
        backoff_limit=4,
        template=k8s.core.v1.PodTemplateSpecArgs(
            spec=k8s.core.v1.PodSpecArgs(
                service_account_name=ksa_name,
                security_context=k8s.core.v1.PodSecurityContextArgs(
                    fs_group=1000,
                ),
                restart_policy="Never",
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="vector-db-loader",
                        image=vector_db_cli_tag.apply(lambda tags: tags[0]),
                        env=[
                            k8s.core.v1.EnvVarArgs(
                                name="GCP_PROJECT", value=project
                            ),
                            k8s.core.v1.EnvVarArgs(
                                name="CHROMADB_HOST", value="vector-db-test"
                            ),
                            k8s.core.v1.EnvVarArgs(
                                name="CHROMADB_PORT", value="8000"
                            ),
                        ],
                        command=[
                            "cli.py",
                            "--download",
                            "--load",
                            "--chunk_type",
                            "recursive-split",
                        ],
                    )
                ],
            ),
        ),
    ),
    opts=ResourceOptions(
        provider=k8s_provider, depends_on=[vector_db_service]
    ),
)

# -----------------------------------------------------------------------------
# API Deployment & Service
# -----------------------------------------------------------------------------
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
                service_account_name=ksa_name,
                security_context=k8s.core.v1.PodSecurityContextArgs(
                    fs_group=1000,
                ),
                volumes=[
                    k8s.core.v1.VolumeArgs(
                        name="persistent-vol",
                        persistent_volume_claim=k8s.core.v1.PersistentVolumeClaimVolumeSourceArgs(
                            claim_name=persistent_pvc.metadata.name,
                        ),
                    )
                ],
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="api",
                        image=api_service_tag.apply(lambda tags: tags[0]),
                        image_pull_policy="IfNotPresent",
                        ports=[
                            k8s.core.v1.ContainerPortArgs(
                                container_port=9000,
                                protocol="TCP",
                            )
                        ],
                        volume_mounts=[
                            k8s.core.v1.VolumeMountArgs(
                                name="persistent-vol",
                                mount_path="/persistent",
                            )
                        ],
                        env=[
                            k8s.core.v1.EnvVarArgs(
                                name="GCS_BUCKET_NAME",
                                value="cheese-app-models",
                            ),
                            k8s.core.v1.EnvVarArgs(
                                name="CHROMADB_HOST",
                                value="vector-db-test",
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
                    )
                ],
            ),
        ),
    ),
    opts=ResourceOptions(
        provider=k8s_provider, depends_on=[vector_db_service]
    ),
)

api_service = k8s.core.v1.Service(
    "api-service",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="api",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.ServiceSpecArgs(
        type="ClusterIP",
        ports=[
            k8s.core.v1.ServicePortArgs(
                port=9000,
                target_port=9000,
                protocol="TCP",
            )
        ],
        selector={"run": "api"},
    ),
    opts=ResourceOptions(provider=k8s_provider, depends_on=[api_deployment]),
)

# -----------------------------------------------------------------------------
# Global IP, Managed Certificate & GCE Ingress
# -----------------------------------------------------------------------------
global_ip = gcp.compute.GlobalAddress(
    "global-static-ip",
    name="cheese-app-global-ip-test",
    address_type="EXTERNAL",
    ip_version="IPV4",
)

host = global_ip.address.apply(lambda ip: f"{ip}.sslip.io")

managed_cert = k8s.apiextensions.CustomResource(
    "managed-cert",
    api_version="networking.gke.io/v1beta1",
    kind="ManagedCertificate",
    metadata={
        "name": "managed-certificates",
        "namespace": namespace.metadata.name,
    },
    spec={"domains": [host]},
    opts=ResourceOptions(provider=k8s_provider, depends_on=[global_ip]),
)

frontend_cfg = k8s.apiextensions.CustomResource(
    "https-redirect",
    api_version="networking.gke.io/v1beta1",
    kind="FrontendConfig",
    metadata={
        "name": "https-redirect",
        "namespace": namespace.metadata.name,
    },
    spec={"redirectToHttps": {"enabled": True}},
    opts=ResourceOptions(provider=k8s_provider),
)

ingress = k8s.networking.v1.Ingress(
    "ac215-ingress",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="ac215-ingress-new",
        namespace=namespace.metadata.name,
        annotations={
            "kubernetes.io/ingress.class": "gce",
            "kubernetes.io/ingress.global-static-ip-name": global_ip.name,
            "networking.gke.io/managed-certificates": "managed-certificates",
            "networking.gke.io/frontend-config": "https-redirect",
        },
    ),
    spec=k8s.networking.v1.IngressSpecArgs(
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
                                    name=frontend_service.metadata.name,
                                    port=k8s.networking.v1.ServiceBackendPortArgs(
                                        number=3000,
                                    ),
                                )
                            ),
                        ),
                        k8s.networking.v1.HTTPIngressPathArgs(
                            path="/api-service",
                            path_type="Prefix",
                            backend=k8s.networking.v1.IngressBackendArgs(
                                service=k8s.networking.v1.IngressServiceBackendArgs(
                                    name=api_service.metadata.name,
                                    port=k8s.networking.v1.ServiceBackendPortArgs(
                                        number=9000,
                                    ),
                                )
                            ),
                        ),
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

# -----------------------------------------------------------------------------
# Stack Outputs
# -----------------------------------------------------------------------------
pulumi.export("cluster_name", cluster.name)
pulumi.export("cluster_endpoint", cluster.endpoint)
pulumi.export("kubeconfig", k8s_provider.kubeconfig)
pulumi.export("namespace", namespace.metadata.name)
pulumi.export("application_url", "https://temp.instel.ai")
