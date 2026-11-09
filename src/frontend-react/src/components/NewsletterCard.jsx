import { Link } from 'react-router'

export default function NewsletterCard({ newsletter }) {
  return (
    <Link
      to={`/newsletters/${newsletter.id}`}
      className="block rounded-2xl border border-line bg-panel p-4.5 hover:border-line-strong"
    >
      <p className="text-sm font-bold text-cheese">
        {newsletter.category} · {newsletter.readTime}
      </p>
      <h3 className="mt-1 mb-1 text-xl font-bold">{newsletter.title}</h3>
      <p className="text-muted">{newsletter.excerpt}</p>
    </Link>
  )
}
