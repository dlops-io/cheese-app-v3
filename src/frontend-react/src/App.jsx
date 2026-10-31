import { useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router'
import { Menu, X } from 'lucide-react'
import { APP_VERSION } from './lib/api'
import { useGet } from './lib/useGet'

const LINKS = [
  { to: '/podcasts', label: 'Podcasts' },
  { to: '/newsletters', label: 'Newsletters' },
]

function Footer() {
  const { data: status } = useGet('/api/status')

  return (
    <footer className="mt-16 border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-wrap justify-between gap-x-6 gap-y-1 px-4 py-7 text-sm text-muted md:px-6">
        <p>Formaggio is a demonstration app from AC215 at Harvard University.</p>
        <p>
          Frontend {APP_VERSION} · API {status?.version ?? 'unknown'}
        </p>
      </div>
    </footer>
  )
}

export default function App() {
  const { pathname } = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const linkStyle = ({ isActive }) => (isActive ? 'text-cream' : 'hover:text-cream')

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="relative flex h-16 flex-none items-center gap-6 border-b border-line px-4 md:px-6">
        <Link to="/" className="flex items-center gap-2.5 font-display text-xl font-bold">
          <img src="/images/logo.png" alt="" className="size-8 rounded-full" />
          Formaggio
        </Link>
        <nav className="ml-auto hidden items-center gap-6 font-semibold text-muted md:flex">
          {LINKS.map(({ to, label }) => (
            <NavLink key={to} to={to} className={linkStyle}>
              {label}
            </NavLink>
          ))}
          <Link to="/chat" className="rounded-full bg-cheese px-4 py-1.5 font-bold text-ink">
            Ask the assistant
          </Link>
        </nav>
        <button
          className="ml-auto p-2 md:hidden"
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
        {menuOpen && (
          <nav
            className="absolute inset-x-0 top-16 z-20 grid gap-1 border-b border-line bg-panel p-3 font-semibold md:hidden"
            onClick={() => setMenuOpen(false)}
          >
            {[...LINKS, { to: '/chat', label: 'Ask the assistant' }].map(({ to, label }) => (
              <Link key={to} to={to} className="rounded-lg px-3 py-2 hover:bg-card">
                {label}
              </Link>
            ))}
          </nav>
        )}
      </header>

      <main className="flex flex-1 flex-col">
        <Outlet />
      </main>

      {pathname !== '/chat' && <Footer />}
    </div>
  )
}
