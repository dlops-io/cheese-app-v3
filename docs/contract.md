# Cheese App API contract

What the browser and `api-service` agree on. Change a route or field in the service, the frontend
and this file together.

The browser calls relative `/api/...` paths on its own origin. Vite forwards them in development,
and the same paths reach the API in production, so nothing strips a prefix and the API needs no CORS.

## Routes

| Route | Sends | Returns |
| --- | --- | --- |
| `GET /api/status` | | `{version}` |
| `GET /api/newsletters?limit=` | | Newsletters, newest first |
| `GET /api/newsletters/{id}` | | One newsletter, or `404` |
| `GET /api/newsletters/image/{name}` | | The image, or `404` |
| `GET /api/podcasts?limit=` | | Podcasts, newest first |
| `GET /api/podcasts/{id}` | | One podcast, or `404` |
| `GET /api/podcasts/audio/{name}` | | The MP3, or `404` |
| `GET /api/{mode}/chats?limit=` | `X-Session-ID` | This session's chats, newest first |
| `GET /api/{mode}/chats/{chat_id}` | `X-Session-ID` | One chat, or `404` |
| `POST /api/{mode}/chats` | `X-Session-ID`, `{content?, image?}` | The new chat |
| `POST /api/{mode}/chats/{chat_id}` | `X-Session-ID`, `{content?, image?}` | The whole chat so far, or `404` |
| `GET /api/{mode}/{image_path}` | | A saved chat image, using a message's `image_path` |
| `GET /api/docs` | | FastAPI's interactive docs |
| `GET /healthz` | | Liveness: the process is up |
| `GET /readyz` | | Readiness: `200` once the CNN model is loaded and Chroma answers, otherwise `503` |

`{mode}` is `llm`, `llm-cnn` or `llm-rag`.

## Chats

- **`X-Session-ID`** is a UUID the browser creates once and keeps in `localStorage`. Use
  `crypto.getRandomValues`, not `crypto.randomUUID()`, which needs HTTPS or localhost. Anything that
  is not a UUID gets `422`.
- **A message** needs `content`, `image` or both, otherwise `422`. `image` is base64, with or without
  a `data:image/...;base64,` prefix.
- **A chat** is `{chat_id, title, dts, messages}`.
- **A message in a chat** is one of:
  - `{message_id, role: "user", content, image_path?}`
  - `{message_id, role: "assistant", content}`
  - `{message_id, role: "cnn", results: {prediction_label, accuracy}}`
- **In `llm-cnn` mode**, an image goes to the classifier and gets a `cnn` reply. Text goes to Gemini,
  which knows what the classifier said.

## Errors

| Status | Meaning |
| --- | --- |
| `400` | The image could not be read |
| `404` | No such chat or content |
| `422` | Missing or invalid session ID, or an empty message |
| `502` | Gemini or Cloud Storage failed, with the reason in `detail` |
| `503` | The CNN model is still loading, or Chroma is down or empty, with the reason in `detail` |

## Settings

Environment variables, read at startup (`api/settings.py`).

| Key | Default | Effect |
| --- | --- | --- |
| `GCP_PROJECT` | required | Your Google Cloud project |
| `GCP_LOCATION` | `global` | Vertex AI location. Current Gemini models are not served from regions such as `us-central1` |
| `GENERATIVE_MODEL` | `gemini-3.8-flash` | The Gemini model |
| `EMBEDDING_MODEL` | `text-embedding-004` | Must match what `vector-db` loaded with |
| `CHROMADB_HOST`, `CHROMADB_PORT` | `cheese-app-vector-db`, `8000` | The Chroma server |
| `PERSISTENT_DIR` | `/persistent` | The CNN model, and chat history when `CHAT_BUCKET` is empty |
| `CHAT_BUCKET` | empty | A Cloud Storage bucket for chat history, so every copy of the API sees the same chats |
