import glob
import json
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

# Define Router
router = APIRouter()

# Newsletters should be downloaded from a GCS bucket (ML Task generates and saves into a bucket)
# We will assume the Newsletters have already been downloaded into "news-letters" folder locally
data_folder = "news-letters"


@router.get("")
def get_newsletters(limit: int | None = None):
    """Get all newsletters, newest first, optionally limited to a specific number"""
    newsletters = []
    for filepath in glob.glob(os.path.join(data_folder, "*.json")):
        with open(filepath, encoding="utf-8") as f:
            newsletters.append(json.load(f))

    newsletters.sort(key=lambda x: x.get("dts", 0), reverse=True)
    return newsletters[:limit] if limit else newsletters


@router.get("/{newsletter_id}")
def get_newsletter(newsletter_id: str):
    """Get a specific newsletter by ID"""
    filepath = os.path.join(data_folder, f"{newsletter_id}.json")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Newsletter not found")
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


@router.get("/image/{image_name}")
def get_newsletter_image(image_name: str):
    image_path = os.path.join(data_folder, "assets", image_name)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Newsletter image not found")
    return FileResponse(image_path)
