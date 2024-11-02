'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

export default function Header() {
    const [isScrolled, setIsScrolled] = useState(false)
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 50)
        }

        window.addEventListener('scroll', handleScroll)
        return () => window.removeEventListener('scroll', handleScroll)
    }, [])

    return (
        <header
            className={`fixed w-full top-0 z-50 transition-all duration-300 ${isScrolled ? 'bg-black/90' : 'bg-transparent'
                }`}
        >
            <div className="container mx-auto px-4 h-20 flex items-center justify-between">
                <Link href="/" className="text-white hover:text-white/90 transition-colors">
                    <h1 className="text-2xl font-bold font-montserrat">🧀 Formaggio</h1>
                </Link>

                {/* Desktop Navigation */}
                <nav className="hidden md:flex gap-8">
                    <Link href="/" className="text-white hover:text-white/90 transition-colors">
                        Home
                    </Link>
                    <Link href="#about" className="text-white hover:text-white/90 transition-colors">
                        About
                    </Link>
                    <Link href="#podcasts" className="text-white hover:text-white/90 transition-colors">
                        Podcasts
                    </Link>
                </nav>

                {/* Mobile Menu Button */}
                <button
                    className="md:hidden p-2"
                    onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                    aria-label="Toggle mobile menu"
                >
                    <div className={`w-6 h-0.5 bg-white mb-1.5 transition-all ${isMobileMenuOpen ? 'rotate-45 translate-y-2' : ''}`} />
                    <div className={`w-6 h-0.5 bg-white mb-1.5 ${isMobileMenuOpen ? 'opacity-0' : ''}`} />
                    <div className={`w-6 h-0.5 bg-white transition-all ${isMobileMenuOpen ? '-rotate-45 -translate-y-2' : ''}`} />
                </button>

                {/* Mobile Menu */}
                <div
                    className={`
            fixed md:hidden top-20 left-0 w-full bg-white shadow-lg transform transition-transform duration-300
            ${isMobileMenuOpen ? 'translate-y-0' : '-translate-y-full'}
          `}
                >
                    <nav className="flex flex-col p-4">
                        <Link
                            href="/"
                            className="py-3 text-gray-800 border-b border-gray-200"
                            onClick={() => setIsMobileMenuOpen(false)}
                        >
                            Home
                        </Link>
                        <Link
                            href="#about"
                            className="py-3 text-gray-800 border-b border-gray-200"
                            onClick={() => setIsMobileMenuOpen(false)}
                        >
                            About
                        </Link>
                        <Link
                            href="#podcasts"
                            className="py-3 text-gray-800"
                            onClick={() => setIsMobileMenuOpen(false)}
                        >
                            Podcasts
                        </Link>
                    </nav>
                </div>
            </div>
        </header>
    )
}