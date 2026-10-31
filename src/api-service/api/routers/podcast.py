import glob
import json
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

# Define Router
router = APIRouter()

# Podcasts should be downloaded from a GCS bucket (ML Task generates and saves into a bucket)
# We will assume the Podcasts have already been downloaded into "podcasts" folder locally
data_folder = "podcasts"


@router.get("")
def get_podcasts(limit: int | None = None):
    """Get all podcasts, newest first, optionally limited to a specific number"""
    podcasts = []
    for filepath in glob.glob(os.path.join(data_folder, "*.json")):
        with open(filepath, encoding="utf-8") as f:
            podcasts.append(json.load(f))

    podcasts.sort(key=lambda x: x.get("dts", 0), reverse=True)
    return podcasts[:limit] if limit else podcasts


@router.get("/{podcast_id}")
def get_podcast(podcast_id: str):
    """Get a specific podcast by ID"""
    filepath = os.path.join(data_folder, f"{podcast_id}.json")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Podcast not found")
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


@router.get("/audio/{audio_name}")
def get_podcast_audio(audio_name: str):
    """Serve the MP3 file for a specific podcast episode"""
    audio_path = os.path.join(data_folder, "assets", audio_name)
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Podcast audio not found")
    return FileResponse(audio_path, media_type="audio/mpeg")
