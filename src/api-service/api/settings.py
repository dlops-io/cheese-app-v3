"""Every setting the API reads, in one place. Environment variables, read once at startup."""

import os

GCP_PROJECT = os.environ["GCP_PROJECT"]
# Current Gemini models answer on the global endpoint only: a region such as us-central1 gives a 404
GCP_LOCATION = os.getenv("GCP_LOCATION", "global")

# When Google retires a model, this is the only line to change
GENERATIVE_MODEL = os.getenv("GENERATIVE_MODEL", "gemini-3.8-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
EMBEDDING_DIMENSION = 256

CHROMADB_HOST = os.getenv("CHROMADB_HOST", "cheese-app-vector-db")
CHROMADB_PORT = int(os.getenv("CHROMADB_PORT", "8000"))

PERSISTENT_DIR = os.getenv("PERSISTENT_DIR", "/persistent")
CHAT_BUCKET = os.getenv("CHAT_BUCKET", "")  # empty: chats stay in PERSISTENT_DIR, for one API on a laptop

# The trained cheese classifier. Downloaded from Github for easy access; after training, this would
# come from your own GCS bucket.
CNN_EXPERIMENT = "experiment_1760994796"
CNN_MODEL_FILE = "mobilenetv2_train_base_True.keras"
CNN_PACKET_URL = f"https://github.com/dlops-io/models/releases/download/v4.0/{CNN_EXPERIMENT}.zip"
