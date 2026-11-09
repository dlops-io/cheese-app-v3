import { useRef, useState } from 'react'
import { ArrowUp, Camera, X } from 'lucide-react'
import { shrinkImage } from '../lib/image'

// The message box on Home and in Chat: text, a photo, or both
export default function Composer({ onSend, placeholder, busy = false }) {
  const [text, setText] = useState('')
  const [image, setImage] = useState(null)
  const [error, setError] = useState('')
  const fileInput = useRef(null)

  async function pickImage(event) {
    const file = event.target.files?.[0]
    event.target.value = '' // so picking the same photo again still counts as a change
    if (!file) return
    try {
      setImage(await shrinkImage(file))
      setError('')
    } catch {
      setError("That file can't be read as a photo. Try a JPEG or PNG.")
    }
  }

  function send() {
    if (busy || (!text.trim() && !image)) return
    onSend({ content: text.trim(), image })
    setText('')
    setImage(null)
  }

  function onKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      send()
    }
  }

  return (
    <div>
      <div className="rounded-2xl border border-line-strong bg-panel p-2 focus-within:border-cheese">
        {image && (
          <div className="relative mb-2 ml-1 w-fit">
            <img src={image} alt="Your photo" className="h-20 rounded-lg" />
            <button
              className="absolute -top-2 -right-2 rounded-full bg-cream p-0.5 text-ink"
              aria-label="Remove photo"
              onClick={() => setImage(null)}
            >
              <X size={14} />
            </button>
          </div>
        )}
        <div className="flex items-end gap-1">
          <input
            ref={fileInput}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={pickImage}
          />
          <button
            className="grid size-10 flex-none place-items-center rounded-xl text-muted hover:text-cream"
            aria-label="Add a photo"
            onClick={() => fileInput.current.click()}
          >
            <Camera size={20} />
          </button>
          <textarea
            rows={1}
            value={text}
            placeholder={placeholder}
            aria-label="Message"
            className="field-sizing-content max-h-40 min-w-0 flex-1 resize-none bg-transparent py-2 outline-none placeholder:text-muted"
            onChange={(event) => setText(event.target.value)}
            onKeyDown={onKeyDown}
          />
          <button
            className="grid size-10 flex-none place-items-center rounded-xl bg-cheese text-ink disabled:opacity-50"
            aria-label="Send"
            disabled={busy}
            onClick={send}
          >
            <ArrowUp size={20} />
          </button>
        </div>
      </div>
      {error && <p className="mt-2 text-sm text-danger">{error}</p>}
    </div>
  )
}
