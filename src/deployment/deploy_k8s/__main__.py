import os

import pulumi
from create_cluster import create_cluster
from create_network import create_network

# Get project info and configuration
project = pulumi.Config("gcp").require("project")
region = os.environ["GCP_REGION"]
zone = os.environ["GCP_ZONE"]
app_name = "cheese-app"

# Create the required network setups
network, subnet, router, nat = create_network(region, f"{app_name}-k8s")

# Create the cluster and its node pool. deploy_k8s only creates the cluster; the workloads are YAML.
cluster, node_pool = create_cluster(project, zone, network, subnet, app_name)

# Export values
pulumi.export("cluster_name", cluster.name)
pulumi.export("cluster_location", cluster.location)
pulumi.export("cluster_endpoint", cluster.endpoint)
pulumi.export("master_version", cluster.master_version)
pulumi.export("node_pool", node_pool.name)
pulumi.export(
    "get_credentials",
    pulumi.Output.concat(
        "gcloud container clusters get-credentials ", cluster.name, f" --zone {zone} --project {project}"
    ),
)
