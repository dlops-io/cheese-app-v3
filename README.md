# Cheese App - Deployment & Scaling


## Deployment to GCP (Manual)
In this section we will deploy the Cheese App to GCP. For this we will create a VM instance in GCP and deploy the following container on the VM:
* api-service
* frontend-react


### Ensure you have all your container build and works locally
#### api-service
* Go to `http://localhost:9000/docs` and make sure you can see the API Docs
#### frontend-react
* Go to `http://localhost:3000/` and make sure you can see the home page

### Push Docker Images to Docker Hub
* Sign up in Docker Hub and create an [Access Token](https://hub.docker.com/settings/security)
* Open a new terminal
* Login to the Hub: `docker login -u <USER NAME> -p <ACCESS TOKEN>`


#### Build, Tag & Push api-service
* Inside the folder `api-service`, make sure you are not in the docker shell
* Build and Tag the Docker Image: `docker build -t <USER NAME>/cheese-app-api-service -f Dockerfile .`
* If you are on M1/2 Macs: Build and Tag the Docker Image: `docker build -t <USER NAME>/cheese-app-api-service --platform=linux/amd64/v2 -f Dockerfile .`
* Push to Docker Hub: `docker push <USER NAME>/cheese-app-api-service`

#### Build, Tag & Push frontend-react
* We need to rebuild the frontend as we are building th react app for production release. So we use the `Dockerfile` instead of the `Docker.dev` file
* Inside the folder`frontend-react`, make sure you are not in the docker shell
* Build and Tag the Docker Image: `docker build -t  <USER NAME>/cheese-app-frontend -f Dockerfile .`
* Push to Docker Hub: `docker push <USER NAME>/cheese-app-frontend`

Docker Build, Tag & Push commands should look like this:
```
docker build -t dlops/cheese-app-api-service --platform=linux/amd64/v2 -f Dockerfile .
docker push dlops/cheese-app-api-service

docker build -t dlops/cheese-app-frontend --platform=linux/amd64/v2 -f Dockerfile .
docker push dlops/cheese-app-frontend
```

### Running Docker Containers on VM

#### Install Docker on VM
* Create a VM Instance from [GCP](https://console.cloud.google.com/compute/instances)
* When creating the VM, you can select all the default values but ensure to select:
	- Machine Type: N2D
	- Allow HTTP traffic
	- Allow HTTPS traffic
* SSH into your newly created instance
Install Docker on the newly created instance by running
* `curl -fsSL https://get.docker.com -o get-docker.sh`
* `sudo sh get-docker.sh`
Check version of installed Docker
* `sudo docker --version`

#### Create folders and give permissions
* `sudo mkdir persistent-folder`
* `sudo mkdir secrets`
* `sudo mkdir -p conf/nginx`
* `sudo chmod 0777 persistent-folder`
* `sudo chmod 0777 secrets`
* `sudo chmod -R 0777 conf`

```
sudo mkdir persistent-folder
sudo mkdir secrets
sudo mkdir -p conf/nginx
sudo chmod 0777 persistent-folder
sudo chmod 0777 secrets
sudo chmod -R 0777 conf
```

#### Add secrets file
* Create a file `gcp-service.json` inside `secrets` folder with the secrets json provided [PP: WHICH ONE] [SJ: This Key need Gemini access so we cannot give it out]
* You can create a file using the echo command:
```
echo '<___Json Key___>' > secrets/gcp-service.json
```


#### Create Docker network
```
sudo docker network create cheese-app-network
```

#### Run api-service
Run the container using the following command
```
sudo docker run -d --name api-service \
-v "$(pwd)/persistent-folder/":/persistent \
-v "$(pwd)/secrets/":/secrets \
-p 9000:9000 \
-e GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-service.json \
-e GCS_BUCKET_NAME=cheese-app-models \
-e GCP_PROJECT=ac215-project \
-e CHROMADB_HOST=cheese-app-vector-db \
-e CHROMADB_PORT=8000 \
--network cheese-app-network dlops/cheese-app-api-service
```


If you want to run in interactive mode like we did in development:
```
sudo docker run --rm -ti --name api-service \
-v "$(pwd)/persistent-folder/":/persistent \
-v "$(pwd)/secrets/":/secrets \
-p 9000:9000 \
-e GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-service.json \
-e GCP_PROJECT=ac215-project \
-e GCP_PROJECT_ID=ac215-project \
-e CHROMADB_HOST=cheese-app-vector-db \
-e CHROMADB_PORT=8000 \
-e GCS_BUCKET_NAME=cheese-app-models \
-e DEV=1 \
--network cheese-app-network dlops/cheese-app-api-service
```

#### Run frontend
Run the container using the following command
```
sudo docker run -d --name frontend -p 3000:3000 --network cheese-app-network dlops/cheese-app-frontend
```

#### Add NGINX config file
* Create `nginx.conf`
```
echo 'user  nginx;
error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;
events {
    worker_connections  1024;
}
http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';
    access_log  /var/log/nginx/access.log  main;
    sendfile        on;
    tcp_nopush     on;
    keepalive_timeout  65;
	types_hash_max_size 2048;
	server_tokens off;
    gzip  on;
	gzip_disable "msie6";

	ssl_protocols TLSv1 TLSv1.1 TLSv1.2; # Dropping SSLv3, ref: POODLE
    ssl_prefer_server_ciphers on;

	server {
		listen 80;

		server_name localhost;

		error_page   500 502 503 504  /50x.html;
		location = /50x.html {
			root   /usr/share/nginx/html;
		}
		# API 
		location ^~ /api/ {
			# Remove the rewrite since we want to preserve the full path after /api/
			proxy_pass http://api-service:9000/;
			proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
			proxy_set_header X-Forwarded-Proto $scheme;
			proxy_set_header X-Real-IP $remote_addr;
			proxy_set_header Host $http_host;
			proxy_redirect off;
			proxy_buffering off;
		}
		
		# Frontend
		location / {
			proxy_pass http://frontend:3000;
			proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
			proxy_set_header X-Forwarded-Proto $scheme;
			proxy_set_header X-Real-IP $remote_addr;
			proxy_set_header Host $http_host;
			proxy_redirect off;
			proxy_buffering off;
		}
	}
}
' > conf/nginx/nginx.conf
```

#### Run NGINX Web Server
Run the container using the following command
```
sudo docker run -d --name nginx -v $(pwd)/conf/nginx/nginx.conf:/etc/nginx/nginx.conf -p 80:80 --network cheese-app-network nginx:stable
```

You can access the deployed API using `http://<Your VM IP Address>/`


## Deployment to GCP

In this section we will deploy the Cheese App to GCP using Ansible Playbooks. We will automate all the deployment steps we did previously.

### API's to enable in GCP before you begin
Search for each of these in the GCP search bar and click enable to enable these API's
* Compute Engine API
* Service Usage API
* Cloud Resource Manager API
* Google Container Registry API

#### Setup GCP Service Account for deployment
- Here are the step to create a service account:
- To setup a service account you will need to go to [GCP Console](https://console.cloud.google.com/home/dashboard), search for  "Service accounts" from the top search box. or go to: "IAM & Admins" > "Service accounts" from the top-left menu and create a new service account called "deployment". 
- Give the following roles:
- For `deployment`:
    - Compute Admin
    - Compute OS Login
    - Container Registry Service Agent
    - Kubernetes Engine Admin
    - Service Account User
    - Storage Admin
- Then click done.
- This will create a service account
- On the right "Actions" column click the vertical ... and select "Create key". A prompt for Create private key for "deployment" will appear select "JSON" and click create. This will download a Private key json file to your computer. Copy this json file into the **secrets** folder.
- Rename the json key file to `deployment.json`
- Follow the same process Create another service account called `gcp-service`
- For `gcp-service` give the following roles:
    - Storage Object Viewer
    - Vertex AI Administrator
- Then click done.
- This will create a service account
- On the right "Actions" column click the vertical ... and select "Create key". A prompt for Create private key for "gcp-service" will appear select "JSON" and click create. This will download a Private key json file to your computer. Copy this json file into the **secrets** folder.
- Rename the json key file to `gcp-service.json`

### Setup Docker Container (Ansible, Docker, Kubernetes)

Rather than each of you installing different tools for deployment we will use Docker to build and run a standard container will all required software.

#### Run `deployment` container
- cd into `deployment`
- Go into `docker-shell.sh` and change `GCP_PROJECT` to your project id
- Run `sh docker-shell.sh` 


- Check versions of tools:
```
gcloud --version
ansible --version
kubectl version --client
```

- Check to make sure you are authenticated to GCP
- Run `gcloud auth list`

Now you have a Docker container that connects to your GCP and can create VMs, deploy containers all from the command line


### SSH Setup
#### Configuring OS Login for service account
Run this within the `deployment` container
```
gcloud compute project-info add-metadata --project <YOUR GCP_PROJECT> --metadata enable-oslogin=TRUE
```
example: 
```
gcloud compute project-info add-metadata --project ac215-project --metadata enable-oslogin=TRUE
```

#### Create SSH key for service account
```
cd /secrets
ssh-keygen -f ssh-key-deployment
cd /app
```

### Providing public SSH keys to instances
```
gcloud compute os-login ssh-keys add --key-file=/secrets/ssh-key-deployment.pub
```
From the output of the above command keep note of the username. Here is a snippet of the output 
```
- accountId: ac215-project
    gid: '3906553998'
    homeDirectory: /home/sa_100110341521630214262
    name: users/deployment@ac215-project.iam.gserviceaccount.com/projects/ac215-project
    operatingSystemType: LINUX
    primary: true
    uid: '3906553998'
	...
    username: sa_100110341521630214262
```
The username is `sa_100110341521630214262`

### Deployment Setup
* Add ansible user details in inventory.yml file
* GCP project details in inventory.yml file
* GCP Compute instance details in inventory.yml file


### Deployment

#### Build and Push Docker Containers to Google Artifact Registry
```
ansible-playbook deploy-docker-images.yml -i inventory.yml
```

#### Create Compute Instance (VM) Server in GCP
```
ansible-playbook deploy-create-instance.yml -i inventory.yml --extra-vars cluster_state=present
```

Once the command runs successfully get the IP address of the compute instance from GCP Console and update the appserver>hosts in inventory.yml file

#### Provision Compute Instance in GCP
Install and setup all the required things for deployment.
```
ansible-playbook deploy-provision-instance.yml -i inventory.yml
```

#### Setup Docker Containers in the  Compute Instance
```
ansible-playbook deploy-setup-containers.yml -i inventory.yml
```


You can SSH into the server from the GCP console and see status of containers
```
sudo docker container ls
sudo docker container logs api-service -f
sudo docker container logs frontend -f
sudo docker container logs nginx -f
```

To get into a container run:
```
sudo docker exec -it api-service /bin/bash
sudo docker exec -it nginx /bin/bash
```



#### Configure Nginx file for Web Server
* Create nginx.conf file for defaults routes in web server

#### Setup Webserver on the Compute Instance
```
ansible-playbook deploy-setup-webserver.yml -i inventory.yml
```
Once the command runs go to `http://<External IP>/` 

## **Delete the Compute Instance / Persistent disk**
```
ansible-playbook deploy-create-instance.yml -i inventory.yml --extra-vars cluster_state=absent
```


## Deployment with Scaling using Kubernetes

In this section we will deploy the cheese app to a K8s cluster

### API's to enable in GCP for Project
Search for each of these in the GCP search bar and click enable to enable these API's
* Compute Engine API
* Service Usage API
* Cloud Resource Manager API
* Google Container Registry API
* Kubernetes Engine API

### Start Deployment Docker Container
-  `cd deployment`
- Run `sh docker-shell.sh` or `docker-shell.bat` for windows
- Check versions of tools
`gcloud --version`
`kubectl version`
`kubectl version --client`

- Check if make sure you are authenticated to GCP
- Run `gcloud auth list`

### Build and Push Docker Containers to GCR
**This step is only required if you have NOT already done this**
```
ansible-playbook deploy-docker-images.yml -i inventory.yml
```

### Create & Deploy Cluster
```
ansible-playbook deploy-k8s-cluster.yml -i inventory.yml --extra-vars cluster_state=present
```

Here is how the various services communicate between each other in the Kubernetes cluster.

```mermaid
graph LR
    B[Browser] -->|nginx-ip.sslip.io/| I[Ingress Controller]
    I -->|/| F[Frontend Service<br/>NodePort:3000]
    I -->|/api/| A[API Service<br/>NodePort:9000]
    A -->|vector-db:8000| V[Vector-DB Service<br/>NodePort:8000]

    style I fill:#lightblue
    style F fill:#lightgreen
    style A fill:#lightgreen
    style V fill:#lightgreen
```

### Try some kubectl commands
```
kubectl get all
kubectl get all --all-namespaces
kubectl get pods --all-namespaces
```

```
kubectl get componentstatuses
kubectl get nodes
```

### If you want to shell into a container in a Pod
```
kubectl get pods --namespace=cheese-app-cluster-namespace
kubectl get pod api-5d4878c545-47754 --namespace=cheese-app-cluster-namespace
kubectl exec --stdin --tty api-5d4878c545-47754 --namespace=cheese-app-cluster-namespace  -- /bin/bash
```

### View the App
* Copy the `nginx_ingress_ip` from the terminal from the create cluster command
* Go to `http://<YOUR INGRESS IP>.sslip.io`

### Delete Cluster
```
ansible-playbook deploy-k8s-cluster.yml -i inventory.yml --extra-vars cluster_state=absent
```


---


## Create Kubernetes Cluster Tutorial 

### API's to enable in GCP for Project
We have already done this in the deployment tutorial but in case you have not done that step. Search for each of these in the GCP search bar and click enable to enable these API's
* Compute Engine API
* Service Usage API
* Cloud Resource Manager API
* Google Container Registry API
* Kubernetes Engine API

### Start Deployment Docker Container
-  `cd deployment`
- Run `sh docker-shell.sh` or `docker-shell.bat` for windows
- Check versions of tools
`gcloud --version`
`kubectl version`
`kubectl version --client`

- Check if make sure you are authenticated to GCP
- Run `gcloud auth list`


### Create Cluster
```
gcloud container clusters create test-cluster --num-nodes 2 --zone us-east1-c
```

### Checkout the cluster in GCP
* Go to the Kubernetes Engine menu item to see the cluster details
    - Click on the cluster name to see the cluster details
    - Click on the Nodes tab to view the nodes
    - Click on any node to see the pods running in the node
* Go to the Compute Engine menu item to see the VMs in the cluster

### Try some kubectl commands
```
kubectl get all
kubectl get all --all-namespaces
kubectl get pods --all-namespaces
```

```
kubectl get componentstatuses
kubectl get nodes
```

### Deploy the App
```
kubectl apply -f deploy-k8s-tic-tac-toe.yml
```

### Get the Loadbalancer external IP
```
kubectl get services
```

### View the App
* Copy the `External IP` from the `kubectl get services`
* Go to `http://<YOUR EXTERNAL IP>`


### Delete Cluster
```
gcloud container clusters delete test-cluster --zone us-east1-c
```




---


## Debugging Containers

If you want to debug any of the containers to see if something is wrong

* View running containers
```
sudo docker container ls
```

* View images
```
sudo docker image ls
```

* View logs
```
sudo docker container logs api-service -f
sudo docker container logs frontend -f
sudo docker container logs nginx -f
```

* Get into shell
```
sudo docker exec -it api-service /bin/bash
sudo docker exec -it frontend /bin/bash
sudo docker exec -it nginx /bin/bash
```


```
# Check the init container logs:
kubectl logs -n cheese-app-cluster-namespace job/vector-db-loader -c wait-for-chromadb

# Check the main container logs:
kubectl logs -n cheese-app-cluster-namespace job/vector-db-loader -c vector-db-loader

# Check the job status:
kubectl describe job vector-db-loader -n cheese-app-cluster-namespace



# First, find the pod name for your job
kubectl get pods -n cheese-app-cluster-namespace | grep vector-db-loader

# Then get the logs from that pod (replace <pod-name> with the actual name)
kubectl logs -n cheese-app-cluster-namespace <pod-name>
kubectl logs -n cheese-app-cluster-namespace vector-db-loader-9gr5m

# If you want to see logs from the init container specifically
kubectl logs -n cheese-app-cluster-namespace <pod-name> -c wait-for-chromadb
kubectl logs -n cheese-app-cluster-namespace vector-db-loader-wlfdx -c wait-for-chromadb

# If you want to see logs from the main container
kubectl logs -n cheese-app-cluster-namespace <pod-name> -c vector-db-loader
kubectl logs -n cheese-app-cluster-namespace vector-db-loader-wlfdx -c vector-db-loader

# You can also get logs directly from the job (this will show logs from the most recent pod)
kubectl logs job/vector-db-loader -n cheese-app-cluster-namespace

# To see previous logs if the pod has restarted
kubectl logs job/vector-db-loader -n cheese-app-cluster-namespace --previous


# View logs from the current API pod
kubectl logs deployment/api -n cheese-app-cluster-namespace

# Follow the logs
kubectl logs deployment/api -n cheese-app-cluster-namespace -f
```


