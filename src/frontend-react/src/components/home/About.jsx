export default function About() {
    return (
        <section id="about" className="py-20 bg-white">
            <div className="container mx-auto px-4 max-w-4xl">
                <h2 className="text-3xl md:text-4xl font-playfair text-center mb-10">
                    About Us
                </h2>
                <div className="bg-gray-50 rounded-lg p-8 shadow-sm">
                    <p className="mb-6 text-lg">
                        Welcome to <strong>Formaggio.me</strong>, a web application born out of a passion for
                        both cheese and cutting-edge technology. This site was created as part
                        of a demonstration project for developing applications using large
                        language models (AI).
                    </p>
                    <p className="text-lg">
                        My name is <strong>Pavlos Protopapas</strong>, and I am the instructor of{' '}
                        <strong>AC215</strong>, a course offered at{' '}
                        <strong>Harvard University</strong>.
                    </p>
                </div>
            </div>
        </section>
    )
}