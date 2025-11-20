from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api.routers import newsletter, podcast
from api.routers import llm_chat, llm_cnn_chat
from api.routers import llm_rag_chat, llm_agent_chat

# This is your existing API app
api_app = FastAPI(title="API Server", description="API Server", version="v1")

api_app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@api_app.get("/")
async def get_index():
    return {"message": "Welcome to AC215"}

@api_app.get("/square_root/")
async def square_root(x: float = 1, y: float = 2):
    z = x**2 + y**2
    return z**0.5

# Routers stay the same
api_app.include_router(newsletter.router, prefix="/newsletters")
api_app.include_router(podcast.router, prefix="/podcasts")
api_app.include_router(llm_chat.router, prefix="/llm")
api_app.include_router(llm_cnn_chat.router, prefix="/llm-cnn")
api_app.include_router(llm_rag_chat.router, prefix="/llm-rag")
api_app.include_router(llm_agent_chat.router, prefix="/llm-agent")

# NEW: top-level app that you actually run
app = FastAPI()

# Mount your API under /api-service to match the Ingress rule
app.mount("/api-service", api_app)
