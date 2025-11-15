#!/bin/bash

echo "Container is running!!!"
echo "Architecture: $(uname -m)"
echo "Environment ready! Virtual environment activated."
echo "Python version: $(python --version)"
echo "UV version: $(uv --version)"

# Authenticate gcloud using service account
gcloud auth activate-service-account --key-file $GOOGLE_APPLICATION_CREDENTIALS
gcloud config set project $GCP_PROJECT

# # Activate virtual environment
# echo "Activating virtual environment..."
# source /home/app/.venv/bin/activate

# # Authenticate gcloud using service account
# gcloud auth activate-service-account --key-file $GOOGLE_APPLICATION_CREDENTIALS
# # Set GCP Project Details
# gcloud config set project $GCP_PROJECT
# # Configure GCR
# gcloud auth configure-docker gcr.io -q

# Run Bash for interactive mode
/bin/bash