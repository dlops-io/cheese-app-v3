import './globals.css'
import Header from '@/components/layout/Header'

export const metadata = {
    title: '🧀 Formaggio',
    description: 'Discover the world of cheese through AI',
}

export default function RootLayout({ children }) {
    return (
        <html lang="en">
            <head>
                <link
                    href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600&family=Montserrat:wght@700&family=Playfair+Display:wght@400;700&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body className="min-h-screen">
                <Header />
                <main>{children}</main>
            </body>
        </html>
    )
}