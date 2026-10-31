import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'
import { PanelLeft, Plus } from 'lucide-react'
import ChatMessage from '../components/ChatMessage'
import Composer from '../components/Composer'
import { continueChat, getChat, getChats, startChat } from '../lib/api'

const MODES = [
  {
    model: 'llm',
    label: 'Ask',
    title: 'Ask about cheese',
    hint: 'Pairings, history, how it is made: Gemini answers as a cheese expert.',
  },
  {
    model: 'llm-cnn',
    label: 'Identify',
    title: 'Identify a cheese',
    hint: 'Add a photo and our trained model names the cheese. Then ask about it.',
  },
  {
    model: 'llm-rag',
    label: 'Cheese books',
    title: 'Ask the cheese books',
    hint: 'Answers come only from the library of cheese books.',
  },
]

export default function Chat() {
  const [params, setParams] = useSearchParams()
  const location = useLocation()
  const navigate = useNavigate()
  const mode = MODES.find(({ model }) => model === params.get('model')) ?? MODES[0]
  const { model } = mode
  const chatId = params.get('id')

  const [chat, setChat] = useState(null)
  const [chats, setChats] = useState([])
  const [pending, setPending] = useState(null) // the message waiting for its reply
  const [failed, setFailed] = useState(null) // the message that got no reply
  const [error, setError] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const thread = useRef(null)
  const messageFromHome = useRef(location.state?.message)

  const shown = chat?.chat_id === chatId ? chat : null

  async function send(message) {
    setError('')
    setFailed(null)
    setPending(message)
    try {
      const saved = chatId
        ? await continueChat(model, chatId, message)
        : await startChat(model, message)
      setChat(saved)
      setParams({ model, id: saved.chat_id })
    } catch (e) {
      setError(e.message)
      setFailed(message)
    } finally {
      setPending(null)
    }
  }

  // A message typed on Home arrives here to be sent, once
  useEffect(() => {
    if (!messageFromHome.current) return
    const message = messageFromHome.current
    messageFromHome.current = null
    navigate(location.pathname + location.search, { replace: true, state: null })
    send(message)
  })

  // Opened from the list or a link: load the chat
  useEffect(() => {
    if (!chatId || chat?.chat_id === chatId) return
    let current = true
    getChat(model, chatId)
      .then((loaded) => current && setChat(loaded))
      .catch((e) => current && setError(e.message))
    return () => {
      current = false
    }
  }, [model, chatId, chat])

  // The list of recent chats: this mode's, and fresh after every answer
  useEffect(() => {
    let current = true
    getChats(model)
      .then((loaded) => current && setChats(loaded))
      .catch(() => current && setChats([]))
    return () => {
      current = false
    }
  }, [model, chat])

  // Answers can be long, so show the latest question at the top and let the answer read downwards
  useEffect(() => {
    const questions = thread.current?.querySelectorAll('[data-role="user"]')
    questions?.[questions.length - 1]?.scrollIntoView({ block: 'start' })
  }, [shown, pending])

  function openChat(next) {
    setError('')
    setFailed(null)
    setSidebarOpen(false)
    setParams(next)
  }

  return (
    <div className="relative grid h-[calc(100dvh-4rem)] md:grid-cols-[270px_minmax(0,1fr)]">
      <aside
        className={`absolute inset-y-0 left-0 z-10 w-72 max-w-[85%] overflow-y-auto border-r border-line bg-panel p-3.5 md:static md:block md:w-auto md:max-w-none ${sidebarOpen ? 'block' : 'hidden'}`}
      >
        <button
          className="mb-4 flex w-full items-center justify-center gap-2 rounded-xl border border-line-strong py-2.5 font-bold"
          onClick={() => openChat({ model })}
        >
          <Plus size={18} /> New chat
        </button>
        <p className="mx-2 mb-1.5 text-sm font-bold text-muted">Recent</p>
        {chats.length === 0 && <p className="mx-2 text-sm text-muted">Your chats appear here.</p>}
        {chats.map(({ chat_id, title }) => (
          <button
            key={chat_id}
            className={`block w-full truncate rounded-lg px-2.5 py-2 text-left ${chat_id === chatId ? 'bg-card text-cream' : 'text-muted hover:text-cream'}`}
            onClick={() => openChat({ model, id: chat_id })}
          >
            {title}
          </button>
        ))}
      </aside>

      <div className="flex min-h-0 min-w-0 flex-col">
        <div className="relative flex justify-center border-b border-line px-4 py-3">
          <button
            className="absolute top-1/2 left-3 -translate-y-1/2 p-2 text-muted md:hidden"
            aria-label="Recent chats"
            aria-expanded={sidebarOpen}
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <PanelLeft size={20} />
          </button>
          <div className="flex gap-0.5 rounded-xl bg-panel p-0.5">
            {MODES.map(({ model: value, label }) => (
              <button
                key={value}
                className={`rounded-lg px-2.5 py-1.5 text-sm font-bold sm:px-4 ${value === model ? 'bg-cheese text-ink' : 'text-muted hover:text-cream'}`}
                aria-pressed={value === model}
                onClick={() => openChat({ model: value })}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div
          ref={thread}
          className="flex-1 overflow-y-auto px-4 py-7"
          onClick={() => setSidebarOpen(false)}
        >
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {!shown && !pending && !failed && !chatId && (
              <div className="mt-[12vh] text-center">
                <h1 className="text-4xl font-bold">{mode.title}</h1>
                <p className="mt-2 text-muted">{mode.hint}</p>
              </div>
            )}
            {shown?.messages.map((message) => (
              <ChatMessage key={message.message_id} message={message} model={model} />
            ))}
            {pending && <ChatMessage message={{ ...pending, role: 'user' }} model={model} />}
            {pending && <p className="animate-pulse text-muted">Thinking…</p>}
            {failed && <ChatMessage message={{ ...failed, role: 'user' }} model={model} />}
            {error && (
              <p role="alert" className="rounded-xl border border-danger px-3.5 py-2.5 text-danger">
                {error}
              </p>
            )}
          </div>
        </div>

        <div className="px-4 pt-3 pb-4">
          <div className="mx-auto max-w-3xl">
            <Composer
              onSend={send}
              busy={Boolean(pending)}
              placeholder={shown ? 'Ask a follow-up' : 'Ask, or add a photo'}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
