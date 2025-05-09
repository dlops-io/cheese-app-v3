/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './src/app/**/*.{js,jsx}',
        './src/components/**/*.{js,jsx}',
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Source Sans Pro', 'sans-serif'],
                montserrat: ['Montserrat', 'sans-serif'],
                playfair: ['Playfair Display', 'serif'],
            },
            colors: {
                'chat-bg': '#363636',
            },
        },
    },
    plugins: [
        require('@tailwindcss/typography'),
    ],
}