import { Link, useNavigate } from 'react-router'
import Composer from '../components/Composer'
import NewsletterCard from '../components/NewsletterCard'
import PodcastRow from '../components/PodcastRow'
import { useGet } from '../lib/useGet'

const SUGGESTIONS = ['Build a cheese board', 'How is Brie made?', 'Pair cheese with red wine']

const MODES = [
  { title: 'Ask', text: 'Chat with Gemini, a cheese expert for any question.', model: 'llm' },
  {
    title: 'Identify',
    text: 'Our trained model names the cheese in your photo.',
    model: 'llm-cnn',
  },
  {
    title: 'Cheese books',
    text: 'Answers drawn from a library of cheese books.',
    model: 'llm-rag',
  },
]

function Section({ title, to, linkLabel, children }) {
  return (
    <section className="mt-14">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="text-3xl font-bold">{title}</h2>
        <Link to={to} className="font-bold text-cheese">
          {linkLabel}
        </Link>
      </div>
      {children}
    </section>
  )
}

export default function Home() {
  const navigate = useNavigate()
  const podcasts = useGet('/api/podcasts?limit=2').data ?? []
  const newsletters = useGet('/api/newsletters?limit=2').data ?? []

  // Chat sends it: a photo goes to the classifier, a question to Gemini
  function startChat(message) {
    const model = message.image ? 'llm-cnn' : 'llm'
    navigate(`/chat?model=${model}`, { state: { message } })
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-4 md:px-6">
      <div className="grid items-center gap-6 py-8 md:grid-cols-[1.05fr_1fr] md:gap-12 md:py-14">
        <div>
          <h1 className="text-5xl font-bold md:text-6xl">
            Discover the world of cheese <span className="text-cheese">through AI</span>
          </h1>
          <p className="mt-3.5 max-w-md text-lg text-muted">
            Take a photo to identify a cheese, then ask about its origin, pairings, and history.
          </p>
          <div className="mt-7">
            <Composer onSend={startChat} placeholder="What goes well with Comté?" />
          </div>
          <div className="mt-3.5 flex flex-wrap gap-2">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                className="rounded-full border border-line px-3 py-1.5 text-sm text-muted hover:text-cream"
                onClick={() => startChat({ content: suggestion, image: null })}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
        <img
          src="/images/cheese-platter.webp"
          alt="Three cheeses on a wooden board"
          className="aspect-[4/3] w-full rounded-3xl object-cover"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {MODES.map(({ title, text, model }) => (
          <Link
            key={model}
            to={`/chat?model=${model}`}
            className="rounded-2xl border border-line bg-panel p-5 hover:border-line-strong"
          >
            <div className="mb-3 h-1 w-8 rounded-full bg-cheese" />
            <h3 className="mb-1 text-xl font-bold">{title}</h3>
            <p className="text-muted">{text}</p>
          </Link>
        ))}
      </div>

      {podcasts.length > 0 && (
        <Section title="Podcast" to="/podcasts" linkLabel="All episodes">
          <div className="grid gap-4 md:grid-cols-2">
            {podcasts.map((podcast) => (
              <PodcastRow key={podcast.id} podcast={podcast} />
            ))}
          </div>
        </Section>
      )}

      {newsletters.length > 0 && (
        <Section title="Newsletters" to="/newsletters" linkLabel="All newsletters">
          <div className="grid gap-4 md:grid-cols-2">
            {newsletters.map((newsletter) => (
              <NewsletterCard key={newsletter.id} newsletter={newsletter} />
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}
