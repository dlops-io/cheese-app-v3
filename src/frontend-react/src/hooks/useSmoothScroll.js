import { useEffect } from 'react'

export function useSmoothScroll() {
    useEffect(() => {
        const handleLinkClick = (e) => {
            const href = e.target.getAttribute('href')

            // Check if it's an anchor link
            if (href?.startsWith('#')) {
                e.preventDefault()

                const targetId = href.substring(1)
                const targetElement = document.getElementById(targetId)

                if (targetElement) {
                    const headerOffset = 80 // Height of your fixed header
                    const elementPosition = targetElement.getBoundingClientRect().top
                    const offsetPosition = elementPosition + window.pageYOffset - headerOffset

                    window.scrollTo({
                        top: offsetPosition,
                        behavior: 'smooth'
                    })
                }
            }
        }

        const links = document.querySelectorAll('a[href^="#"]')
        links.forEach(link => {
            link.addEventListener('click', handleLinkClick)
        })

        return () => {
            links.forEach(link => {
                link.removeEventListener('click', handleLinkClick)
            })
        }
    }, [])
}