import { Link } from 'react-router'

export default function NotFound() {
  return (
    <div className="mx-auto mt-24 px-4 text-center">
      <h1 className="text-5xl font-bold">That page isn't here</h1>
      <Link to="/" className="mt-4 inline-block font-bold text-cheese">
        Go to the home page
      </Link>
    </div>
  )
}
