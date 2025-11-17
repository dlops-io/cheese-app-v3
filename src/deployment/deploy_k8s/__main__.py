import os
import pulumi
import pulumi_gcp as gcp
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts
from pulumi import Output

# Get project info and configuration
gcp_config = pulumi.Config("gcp")
project = gcp_config.require("project")
location = os.environ["GCP_REGION"]
zone = os.environ["GCP_ZONE"]

# Cluster configuration
cluster_name = "cheese-app-cluster"
machine_type = "n2d-standard-2"
machine_disk_size = 30
initial_node_count = 2

# Get the image tag from the deploy_images stack
stack_ref = pulumi.StackReference(f"organization/{project}/deploy_images/dev")
# You can get outputs from the deploy_images stack like this:
# api_service_image_ref = stack_ref.get_output("cheese-app-api-service-ref")
# For now, we'll use a placeholder or environment variable for the tag
docker_tag = os.environ.get("DOCKER_TAG", "latest")

# 1. Create GKE Cluster
cluster = gcp.container.Cluster(
    cluster_name,
    name=cluster_name,
    location=zone,
    initial_node_count=initial_node_count,
    remove_default_node_pool=True,  # We'll create a custom node pool
    release_channel=gcp.container.ClusterReleaseChannelArgs(
        channel="UNSPECIFIED",
    ),
    ip_allocation_policy=gcp.container.ClusterIpAllocationPolicyArgs(
        cluster_ipv4_cidr_block="",
        services_ipv4_cidr_block="",
    ),
    deletion_protection=False,  # Set to True in production
)

# 2. Create Node Pool
node_pool = gcp.container.NodePool(
    "default-pool",
    cluster=cluster.name,
    location=zone,
    initial_node_count=initial_node_count,
    node_config=gcp.container.NodePoolNodeConfigArgs(
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
        max_node_count=initial_node_count,
    ),
    management=gcp.container.NodePoolManagementArgs(
        auto_repair=True,
        auto_upgrade=True,
    ),
)

# Create a Kubernetes provider instance that uses the GKE cluster
k8s_provider = k8s.Provider(
    "gke-k8s",
    kubeconfig=Output.all(cluster.name, cluster.endpoint, cluster.master_auth).apply(
        lambda args: f"""apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {args[2].cluster_ca_certificate}
    server: https://{args[1]}
  name: {args[0]}
contexts:
- context:
    cluster: {args[0]}
    user: {args[0]}
  name: {args[0]}
current-context: {args[0]}
kind: Config
preferences: {{}}
users:
- name: {args[0]}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gke-gcloud-auth-plugin
      installHint: Install gke-gcloud-auth-plugin for use with kubectl by following
        https://cloud.google.com/blog/products/containers-kubernetes/kubectl-auth-changes-in-gke
      provideClusterInfo: true
"""
    ),
    opts=pulumi.ResourceOptions(depends_on=[node_pool]),
)

# 3. Create Namespace
namespace = k8s.core.v1.Namespace(
    f"{cluster_name}-namespace",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name=f"{cluster_name}-namespace",
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider),
)

# 4. Install nginx-ingress using Helm
nginx_ingress = Chart(
    "nginx-ingress",
    ChartOpts(
        chart="nginx-ingress",
        version="1.1.3",  # Specify version for reproducibility
        fetch_opts=FetchOpts(
            repo="https://helm.nginx.com/stable",
        ),
        namespace=namespace.metadata.name,
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
)

# 5. Create Persistent Volume Claims
persistent_pvc = k8s.core.v1.PersistentVolumeClaim(
    "persistent-pvc",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="persistent-pvc",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
        access_modes=["ReadWriteOnce"],
        resources=k8s.core.v1.VolumeResourceRequirementsArgs(
            requests={"storage": "5Gi"},
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
)

chromadb_pvc = k8s.core.v1.PersistentVolumeClaim(
    "chromadb-pvc",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="chromadb-pvc",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.PersistentVolumeClaimSpecArgs(
        access_modes=["ReadWriteOnce"],
        resources=k8s.core.v1.VolumeResourceRequirementsArgs(
            requests={"storage": "10Gi"},
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
)

# 6. Create Secret for GCP Service Account
# Note: In Pulumi, you need to read the file and create the secret
# Make sure the path to your GCP service account JSON is correct
gcp_service_key_path = "../secrets/gcp-service.json"
try:
    with open(gcp_service_key_path, "r") as f:
        gcp_service_key_content = f.read()

    gcp_secret = k8s.core.v1.Secret(
        "gcp-service-key",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="gcp-service-key",
            namespace=namespace.metadata.name,
        ),
        string_data={
            "gcp-service.json": gcp_service_key_content,
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
    )
except FileNotFoundError:
    pulumi.log.warn(f"GCP service key file not found at {gcp_service_key_path}. Please ensure it exists before deploying.")
    gcp_secret = None

# 7. Create Deployments

# Frontend Deployment
frontend_deployment = k8s.apps.v1.Deployment(
    "frontend",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="frontend",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.apps.v1.DeploymentSpecArgs(
        selector=k8s.meta.v1.LabelSelectorArgs(
            match_labels={"run": "frontend"},
        ),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(
                labels={"run": "frontend"},
            ),
            spec=k8s.core.v1.PodSpecArgs(
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="frontend",
                        image=f"us-docker.pkg.dev/{project}/cheese-app-repository/cheese-app-frontend-react:{docker_tag}",
                        image_pull_policy="IfNotPresent",
                        ports=[k8s.core.v1.ContainerPortArgs(
                            container_port=3000,
                            protocol="TCP",
                        )],
                    ),
                ],
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace]),
)

# ChromaDB Deployment
vector_db_deployment = k8s.apps.v1.Deployment(
    "vector-db",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="vector-db",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.apps.v1.DeploymentSpecArgs(
        selector=k8s.meta.v1.LabelSelectorArgs(
            match_labels={"run": "vector-db"},
        ),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(
                labels={"run": "vector-db"},
            ),
            spec=k8s.core.v1.PodSpecArgs(
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="vector-db",
                        image="chromadb/chroma:0.5.6",
                        ports=[k8s.core.v1.ContainerPortArgs(
                            container_port=8000,
                            protocol="TCP",
                        )],
                        env=[
                            k8s.core.v1.EnvVarArgs(name="IS_PERSISTENT", value="TRUE"),
                            k8s.core.v1.EnvVarArgs(name="ANONYMIZED_TELEMETRY", value="FALSE"),
                        ],
                        # Uncomment below to use persistent volume
                        # volume_mounts=[
                        #     k8s.core.v1.VolumeMountArgs(
                        #         name="chromadb-storage",
                        #         mount_path="/chroma/chroma",
                        #     ),
                        # ],
                    ),
                ],
                # volumes=[
                #     k8s.core.v1.VolumeArgs(
                #         name="chromadb-storage",
                #         persistent_volume_claim=k8s.core.v1.PersistentVolumeClaimVolumeSourceArgs(
                #             claim_name=chromadb_pvc.metadata.name,
                #         ),
                #     ),
                # ],
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[namespace, chromadb_pvc]),
)

# API Service Deployment
api_deployment_deps = [namespace, persistent_pvc]
if gcp_secret:
    api_deployment_deps.append(gcp_secret)

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
                volumes=[
                    k8s.core.v1.VolumeArgs(
                        name="persistent-vol",
                        empty_dir=k8s.core.v1.EmptyDirVolumeSourceArgs(),
                    ),
                    k8s.core.v1.VolumeArgs(
                        name="google-cloud-key",
                        secret=k8s.core.v1.SecretVolumeSourceArgs(
                            secret_name="gcp-service-key",
                        ),
                    ),
                ],
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="api",
                        image=f"us-docker.pkg.dev/{project}/cheese-app-repository/cheese-app-api-service:{docker_tag}",
                        image_pull_policy="IfNotPresent",
                        ports=[k8s.core.v1.ContainerPortArgs(
                            container_port=9000,
                            protocol="TCP",
                        )],
                        volume_mounts=[
                            k8s.core.v1.VolumeMountArgs(
                                name="persistent-vol",
                                mount_path="/persistent",
                            ),
                            k8s.core.v1.VolumeMountArgs(
                                name="google-cloud-key",
                                mount_path="/secrets",
                            ),
                        ],
                        env=[
                            k8s.core.v1.EnvVarArgs(
                                name="GOOGLE_APPLICATION_CREDENTIALS",
                                value="/secrets/gcp-service.json",
                            ),
                            k8s.core.v1.EnvVarArgs(
                                name="GCS_BUCKET_NAME",
                                value="cheese-app-models",
                            ),
                            k8s.core.v1.EnvVarArgs(
                                name="CHROMADB_HOST",
                                value="vector-db",
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
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=api_deployment_deps),
)

# 8. Create Services

# Frontend Service
frontend_service = k8s.core.v1.Service(
    "frontend-service",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="frontend",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.ServiceSpecArgs(
        type="NodePort",
        ports=[k8s.core.v1.ServicePortArgs(
            port=3000,
            target_port=3000,
            protocol="TCP",
        )],
        selector={"run": "frontend"},
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[frontend_deployment]),
)

# ChromaDB Service
vector_db_service = k8s.core.v1.Service(
    "vector-db-service",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="vector-db",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.ServiceSpecArgs(
        type="NodePort",
        ports=[k8s.core.v1.ServicePortArgs(
            port=8000,
            target_port=8000,
            protocol="TCP",
        )],
        selector={"run": "vector-db"},
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[vector_db_deployment]),
)

# API Service
api_service = k8s.core.v1.Service(
    "api-service",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="api",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.core.v1.ServiceSpecArgs(
        type="NodePort",
        ports=[k8s.core.v1.ServicePortArgs(
            port=9000,
            target_port=9000,
            protocol="TCP",
        )],
        selector={"run": "api"},
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[api_deployment]),
)

# 9. Create Job for Loading Vector DB
vector_db_loader_job = k8s.batch.v1.Job(
    "vector-db-loader",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="vector-db-loader",
        namespace=namespace.metadata.name,
    ),
    spec=k8s.batch.v1.JobSpecArgs(
        backoff_limit=4,
        template=k8s.core.v1.PodTemplateSpecArgs(
            spec=k8s.core.v1.PodSpecArgs(
                restart_policy="Never",
                init_containers=[
                    k8s.core.v1.ContainerArgs(
                        name="wait-for-chromadb",
                        image="busybox:1.28",
                        command=[
                            "sh",
                            "-c",
                            'until wget --spider -S http://vector-db:8000/api/v1/heartbeat 2>&1 | grep "HTTP/1.1 200"; do echo "Waiting for ChromaDB..."; sleep 5; done;',
                        ],
                    ),
                ],
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="vector-db-loader",
                        image=f"us-docker.pkg.dev/{project}/cheese-app-repository/cheese-app-vector-db-cli:{docker_tag}",
                        env=[
                            k8s.core.v1.EnvVarArgs(name="GCP_PROJECT", value=project),
                            k8s.core.v1.EnvVarArgs(name="CHROMADB_HOST", value="vector-db"),
                            k8s.core.v1.EnvVarArgs(name="CHROMADB_PORT", value="8000"),
                            k8s.core.v1.EnvVarArgs(
                                name="GOOGLE_APPLICATION_CREDENTIALS",
                                value="/secrets/gcp-service.json",
                            ),
                        ],
                        volume_mounts=[
                            k8s.core.v1.VolumeMountArgs(
                                name="google-cloud-key",
                                mount_path="/secrets",
                            ),
                        ],
                    ),
                ],
                volumes=[
                    k8s.core.v1.VolumeArgs(
                        name="google-cloud-key",
                        secret=k8s.core.v1.SecretVolumeSourceArgs(
                            secret_name="gcp-service-key",
                        ),
                    ),
                ],
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[vector_db_service, api_deployment] if gcp_secret else [vector_db_service],
    ),
)

# 10. Get nginx-ingress controller service to retrieve the external IP
nginx_ingress_service = k8s.core.v1.Service.get(
    "nginx-ingress-controller",
    Output.concat(namespace.metadata.name, "/nginx-ingress-nginx-ingress"),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[nginx_ingress]),
)

# Extract the LoadBalancer IP
nginx_ingress_ip = nginx_ingress_service.status.apply(
    lambda status: status.load_balancer.ingress[0].ip if status and status.load_balancer.ingress else None
)

# 11. Create Ingress Controller
ingress = k8s.networking.v1.Ingress(
    "ingress-resource",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="ingress-resource",
        namespace=namespace.metadata.name,
        annotations={
            "kubernetes.io/ingress.class": "nginx",
            "nginx.ingress.kubernetes.io/ssl-redirect": "false",
            "nginx.org/rewrites": "serviceName=frontend rewrite=/;serviceName=api rewrite=/",
        },
    ),
    spec=k8s.networking.v1.IngressSpecArgs(
        rules=[
            k8s.networking.v1.IngressRuleArgs(
                host=nginx_ingress_ip.apply(lambda ip: f"{ip}.sslip.io" if ip else "pending.sslip.io"),
                http=k8s.networking.v1.HTTPIngressRuleValueArgs(
                    paths=[
                        k8s.networking.v1.HTTPIngressPathArgs(
                            path="/",
                            path_type="Prefix",
                            backend=k8s.networking.v1.IngressBackendArgs(
                                service=k8s.networking.v1.IngressServiceBackendArgs(
                                    name="frontend",
                                    port=k8s.networking.v1.ServiceBackendPortArgs(number=3000),
                                ),
                            ),
                        ),
                        k8s.networking.v1.HTTPIngressPathArgs(
                            path="/api/",
                            path_type="Prefix",
                            backend=k8s.networking.v1.IngressBackendArgs(
                                service=k8s.networking.v1.IngressServiceBackendArgs(
                                    name="api",
                                    port=k8s.networking.v1.ServiceBackendPortArgs(number=9000),
                                ),
                            ),
                        ),
                    ],
                ),
            ),
        ],
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[frontend_service, api_service, nginx_ingress],
    ),
)

# 12. Export outputs
pulumi.export("cluster_name", cluster.name)
pulumi.export("cluster_endpoint", cluster.endpoint)
pulumi.export("kubeconfig", k8s_provider.kubeconfig)
pulumi.export("namespace", namespace.metadata.name)
pulumi.export("nginx_ingress_ip", nginx_ingress_ip)
pulumi.export("application_url", nginx_ingress_ip.apply(lambda ip: f"http://{ip}.sslip.io" if ip else "pending"))
