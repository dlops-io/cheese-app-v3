// The one way the pages talk to the API. Every path is relative to the page's own origin: Vite
// forwards /api in development and nginx does in production, so there are no addresses here and no
// CORS. Routes and fields: docs/contract.md.

export const APP_VERSION = '3.0.0' // shown in the footer, so a deploy is visible

const SESSION_KEY = 'userSessionId'
let memorySessionId = null // where localStorage is blocked, the session lasts until a reload

// crypto.randomUUID() only exists on HTTPS or localhost, and a deployed app may be plain HTTP
function newUuid() {
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 0x0f) | 0x40 // version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80 // variant
  const hex = [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

function sessionId() {
  try {
    let id = localStorage.getItem(SESSION_KEY)
    if (!id) {
      id = newUuid()
      localStorage.setItem(SESSION_KEY, id)
    }
    return id
  } catch {
    memorySessionId ??= newUuid()
    return memorySessionId
  }
}

async function request(path, body) {
  const options = {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'X-Session-ID': sessionId() },
    signal: AbortSignal.timeout(130_000), // a little longer than the API gives Gemini
  }
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(path, options)
  } catch {
    throw new Error("Couldn't reach the API. Check that it's running.")
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(
      typeof data?.detail === 'string' ? data.detail : `The API answered ${response.status}.`,
    )
  }
  return data
}

export const get = (path) => request(path)

export const getChats = (model) => get(`/api/${model}/chats?limit=30`)
export const getChat = (model, chatId) => get(`/api/${model}/chats/${chatId}`)
export const startChat = (model, message) => request(`/api/${model}/chats`, message)
export const continueChat = (model, chatId, message) =>
  request(`/api/${model}/chats/${chatId}`, message)

export const chatImageUrl = (model, imagePath) => `/api/${model}/${imagePath}`
export const newsletterImageUrl = (name) => `/api/newsletters/image/${name}`
export const podcastAudioUrl = (name) => `/api/podcasts/audio/${name}`
