import PodcastCard from '@/components/shared/PodcastCard'

const podcastData = [
    {
        id: 1,
        title: "Episode 1 (Halloumi) [FR]",
        description: "Discover the wonderful world of Halloumi cheese",
        date: "September 12, 2024",
        duration: "5:36"
    },
    {
        id: 2,
        title: "Episode 1 (Halloumi) [ES]",
        description: "Discover the wonderful world of Halloumi cheese",
        date: "September 12, 2024",
        duration: "5:59"
    }
]

export default function Podcasts() {
    return (
        <section id="podcasts" className="py-20 bg-gray-50">
            <div className="container mx-auto px-4">
                <h2 className="text-3xl md:text-4xl font-playfair text-center mb-10">
                    Podcasts
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
                    {podcastData.map(podcast => (
                        <PodcastCard key={podcast.id} podcast={podcast} />
                    ))}
                </div>
            </div>
        </section>
    )
}