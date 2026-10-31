import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { chatImageUrl } from '../lib/api'

function CnnResult({ results }) {
  return (
    <div className="max-w-sm rounded-2xl border border-line-strong bg-panel px-4 py-3">
      <p className="text-sm font-bold text-muted">Our model thinks this is</p>
      <h3 className="mt-0.5 text-2xl font-bold capitalize">{results.prediction_label}</h3>
      <div className="mt-2 flex items-center gap-3 text-sm font-bold">
        <div className="h-2 flex-1 rounded-full bg-line">
          <div
            className="h-full rounded-full bg-cheese"
            style={{ width: `${results.accuracy}%` }}
          />
        </div>
        {results.accuracy}%
      </div>
    </div>
  )
}

export default function ChatMessage({ message, model }) {
  if (message.role === 'cnn') return <CnnResult results={message.results} />

  if (message.role === 'assistant') {
    return (
      <div className="rich-text">
        {/* Gemini writes markdown. Raw HTML in it stays plain text, so an answer can't run code. */}
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
      </div>
    )
  }

  // While a message is being sent, its photo is still the local copy
  const imageUrl = message.image || (message.image_path && chatImageUrl(model, message.image_path))
  return (
    <div data-role="user" className="flex scroll-mt-2 flex-col items-end gap-2">
      {imageUrl && <img src={imageUrl} alt="Your photo" className="max-h-52 rounded-2xl" />}
      {message.content && (
        <p className="max-w-[85%] rounded-2xl rounded-br-sm bg-card px-3.5 py-2.5 break-words whitespace-pre-wrap">
          {message.content}
        </p>
      )}
    </div>
  )
}
