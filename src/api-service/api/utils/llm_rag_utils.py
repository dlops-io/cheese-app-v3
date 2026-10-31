"""RAG mode: answer from the text chunks Chroma finds for each question."""

from functools import cache

import chromadb
import httpx
from chromadb.errors import ChromaError, NotFoundError
from fastapi import HTTPException
from google.genai import errors, types

from api import settings
from api.utils.chat_utils import ChatHistoryManager
from api.utils.llm_utils import ask_gemini, llm_client, message_parts, to_history

SYSTEM_INSTRUCTION = """
You are an AI assistant specialized in cheese knowledge. Your responses are based solely on the information provided in the text chunks given to you. Do not use any external knowledge or make assumptions beyond what is explicitly stated in these chunks.

When answering a query:
1. Carefully read all the text chunks provided.
2. Identify the most relevant information from these chunks to address the user's question.
3. Formulate your response using only the information found in the given chunks.
4. If the provided chunks do not contain sufficient information to answer the query, state that you don't have enough information to provide a complete answer.
5. Always maintain a professional and knowledgeable tone, befitting a cheese expert.
6. If there are contradictions in the provided chunks, mention this in your response and explain the different viewpoints presented.

Remember:
- You are an expert in cheese, but your knowledge is limited to the information in the provided chunks.
- Do not invent information or draw from knowledge outside of the given text chunks.
- If asked about topics unrelated to cheese, politely redirect the conversation back to cheese-related subjects.
- Be concise in your responses while ensuring you cover all relevant information from the chunks.

Your goal is to provide accurate, helpful information about cheese based solely on the content of the text chunks you receive with each query.
"""

COLLECTION_NAME = "recursive-split-collection"


@cache
def chroma_client() -> chromadb.ClientAPI:
    """Connect on first use, so the API can start before Chroma does. A failed connection is not
    cached, so the next call tries again."""
    return chromadb.HttpClient(host=settings.CHROMADB_HOST, port=settings.CHROMADB_PORT)


def generate_query_embedding(query: str) -> list[float]:
    try:
        response = llm_client.models.embed_content(
            model=settings.EMBEDDING_MODEL,
            contents=query,
            config=types.EmbedContentConfig(output_dimensionality=settings.EMBEDDING_DIMENSION),
        )
    except errors.APIError as e:
        raise HTTPException(status_code=502, detail=f"Gemini: {e}")
    return response.embeddings[0].values


def find_chunks(query: str) -> list[str]:
    embedding = generate_query_embedding(query)
    try:
        collection = chroma_client().get_collection(name=COLLECTION_NAME)
        results = collection.query(query_embeddings=[embedding], n_results=5)
    except NotFoundError:
        raise HTTPException(status_code=503, detail="The vector DB is empty: load it first (see vector-db)")
    except (ChromaError, ValueError, httpx.TransportError) as e:
        raise HTTPException(status_code=503, detail=f"Chroma: {e}")
    return results["documents"][0]


def respond(chat_manager: ChatHistoryManager, past_messages: list[dict], message: dict) -> dict:
    if message.get("image"):
        parts = message_parts(message)
    else:
        chunks = "\n".join(find_chunks(message["content"]))
        parts = [f"{message['content']}\n{chunks}"]
    history = to_history(past_messages, chat_manager)
    return {"role": "assistant", "content": ask_gemini(SYSTEM_INSTRUCTION, history, parts)}
