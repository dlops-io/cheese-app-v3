import PodcastRow from '../components/PodcastRow'
import { useGet } from '../lib/useGet'

export default function Podcasts() {
  const { data: podcasts, error } = useGet('/api/podcasts')

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 md:px-6">
      <h1 className="text-5xl font-bold">Cheese Voices</h1>
      <p className="mt-2 text-lg text-muted">
        Where AI meets artisanal expertise: a podcast series on artificial intelligence and cheese
        appreciation.
      </p>
      {error && <p className="mt-8 text-danger">{error}</p>}
      <div className="mt-8 grid gap-4">
        {podcasts?.map((podcast) => (
          <PodcastRow key={podcast.id} podcast={podcast} />
        ))}
      </div>
    </div>
  )
}
