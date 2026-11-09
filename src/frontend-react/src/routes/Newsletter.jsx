import { Link, useParams } from 'react-router'
import { newsletterImageUrl } from '../lib/api'
import { useGet } from '../lib/useGet'

export default function Newsletter() {
  const { id } = useParams()
  const { data: newsletter, error } = useGet(`/api/newsletters/${id}`)

  return (
    <article className="mx-auto w-full max-w-3xl px-4 py-10 md:px-6">
      <Link to="/newsletters" className="font-bold text-cheese">
        All newsletters
      </Link>
      {error && <p className="mt-6 text-danger">{error}</p>}
      {newsletter && (
        <>
          <p className="mt-6 text-sm font-bold text-cheese">
            {newsletter.category} · {newsletter.readTime}
          </p>
          <h1 className="mt-1 text-5xl font-bold">{newsletter.title}</h1>
          <img
            src={newsletterImageUrl(newsletter.image)}
            alt=""
            className="mt-6 w-full max-w-xs rounded-2xl"
          />
          {/* The newsletters are our own files, written as HTML: not text from a visitor */}
          <div className="rich-text mt-6" dangerouslySetInnerHTML={{ __html: newsletter.detail }} />
        </>
      )}
    </article>
  )
}
