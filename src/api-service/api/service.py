"""Cheese App API. Everything the browser calls is under /api; the probes stay at the root.

/api/newsletters, /api/podcasts      content
/api/llm, /api/llm-cnn, /api/llm-rag chat, one router per mode (see routers/chat.py)
/api/docs                            FastAPI's interactive docs
/healthz                             liveness: the process is up
/readyz                              readiness: the CNN model is loaded and Chroma answers
"""

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from google.api_core.exceptions import GoogleAPIError

from api.routers import chat, newsletter, podcast
from api.utils import llm_cnn_utils, llm_rag_utils, llm_utils


@asynccontextmanager
async def lifespan(app: FastAPI):
    # In the background, so the API answers while the model loads; /readyz says when it is done
    threading.Thread(target=llm_cnn_utils.load_cnn_model, daemon=True).start()
    yield


app = FastAPI(
    title="Cheese App API", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json"
)


@app.exception_handler(GoogleAPIError)
def cloud_storage_failed(request, error: GoogleAPIError):
    return JSONResponse(status_code=502, content={"detail": f"Cloud Storage: {error}"})


@app.get("/api/status")
def get_status():
    return {"version": "3.0.0"}


app.include_router(newsletter.router, prefix="/api/newsletters")
app.include_router(podcast.router, prefix="/api/podcasts")
app.include_router(chat.create_router("llm", llm_utils.respond), prefix="/api/llm")
app.include_router(chat.create_router("llm-cnn", llm_cnn_utils.respond), prefix="/api/llm-cnn")
app.include_router(chat.create_router("llm-rag", llm_rag_utils.respond), prefix="/api/llm-rag")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/readyz")
def readyz():
    if llm_cnn_utils.cnn_model is None:
        raise HTTPException(503, "CNN model is loading")
    try:
        llm_rag_utils.chroma_client().heartbeat()
    except Exception as e:  # noqa: BLE001 - whatever went wrong, this pod is not ready
        raise HTTPException(503, f"Chroma: {e}")
    return {"ok": True}
