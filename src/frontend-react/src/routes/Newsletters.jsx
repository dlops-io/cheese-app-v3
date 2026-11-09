import NewsletterCard from '../components/NewsletterCard'
import { useGet } from '../lib/useGet'

export default function Newsletters() {
  const { data: newsletters, error } = useGet('/api/newsletters')

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 md:px-6">
      <h1 className="text-5xl font-bold">Cheese Chronicles</h1>
      <p className="mt-2 max-w-xl text-lg text-muted">
        Artisanal cheese-making, tasting notes, and the latest in cheese technology.
      </p>
      {error && <p className="mt-8 text-danger">{error}</p>}
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        {newsletters?.map((newsletter) => (
          <NewsletterCard key={newsletter.id} newsletter={newsletter} />
        ))}
      </div>
    </div>
  )
}
