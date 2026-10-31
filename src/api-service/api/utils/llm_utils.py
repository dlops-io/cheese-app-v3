"""Chat with Gemini: the plain LLM mode, and the pieces the other modes build on."""

import io

from fastapi import HTTPException
from google import genai
from google.genai import errors, types
from PIL import Image, UnidentifiedImageError

from api import settings
from api.utils.chat_utils import ChatHistoryManager, decode_image

#############################################################################
#                       Initialize the LLM Client                           #
llm_client = genai.Client(vertexai=True, project=settings.GCP_PROJECT, location=settings.GCP_LOCATION)
#############################################################################

SYSTEM_INSTRUCTION = """
You are an AI assistant specialized in cheese knowledge.

When answering a query:
1. Demonstrate expertise in cheese, including aspects like:
  - Production methods and techniques
  - Flavor profiles and characteristics
  - Aging processes and requirements
  - Regional varieties and traditions
  - Pairing recommendations
  - Storage and handling best practices
2. Always maintain a professional and knowledgeable tone, befitting a cheese expert.

Your goal is to provide accurate, helpful information about cheese for each query.
"""

IMAGE_PROMPT = "Name the cheese in the image, no descriptions needed"


def image_part(image_bytes: bytes) -> types.Part:
    """An image for Gemini. The bytes say what kind of image it is, whatever the file is called."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            mime_type = image.get_format_mimetype()
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Image processing failed: not an image")
    return types.Part.from_bytes(data=image_bytes, mime_type=mime_type)


def message_parts(message: dict) -> list:
    """A new message as parts for Gemini: an image needs some text with it"""
    if message.get("image"):
        return [image_part(decode_image(message["image"])), message.get("content") or IMAGE_PROMPT]
    return [message["content"]]


def to_history(messages: list[dict], chat_manager: ChatHistoryManager) -> list[types.Content]:
    """The saved messages of a chat, in the form Gemini takes as history"""
    history = []
    for message in messages:
        if message["role"] == "assistant":
            history.append(types.ModelContent(parts=[types.Part.from_text(text=message["content"])]))
        elif message["role"] == "cnn":
            label = message["results"]["prediction_label"]
            text = f"We have already identified the image of a cheese as {label}"
            history.append(types.UserContent(parts=[types.Part.from_text(text=text)]))
        elif message["role"] == "user":
            parts = []
            image_bytes = (
                chat_manager.load_image(message["image_path"]) if message.get("image_path") else None
            )
            if image_bytes:
                parts.append(image_part(image_bytes))
            text = message.get("content") or (IMAGE_PROMPT if image_bytes else "")
            if text:
                parts.append(types.Part.from_text(text=text))
            if parts:
                history.append(types.UserContent(parts=parts))
    return history


def ask_gemini(system_instruction: str, history: list[types.Content], parts: list) -> str:
    """Send one message to Gemini, with the conversation so far"""
    config = types.GenerateContentConfig(system_instruction=system_instruction)
    chat = llm_client.chats.create(model=settings.GENERATIVE_MODEL, config=config, history=history)
    try:
        text = chat.send_message(parts).text
    except errors.APIError as e:
        raise HTTPException(status_code=502, detail=f"Gemini: {e}")
    if not text:
        raise HTTPException(status_code=502, detail="Gemini returned no text")
    return text


def respond(chat_manager: ChatHistoryManager, past_messages: list[dict], message: dict) -> dict:
    history = to_history(past_messages, chat_manager)
    return {"role": "assistant", "content": ask_gemini(SYSTEM_INSTRUCTION, history, message_parts(message))}
