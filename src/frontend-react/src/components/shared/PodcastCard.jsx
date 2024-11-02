export default function PodcastCard({ podcast }) {
    return (
        <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
            <div className="p-6">
                <h3 className="text-xl font-semibold mb-2">{podcast.title}</h3>
                <p className="text-gray-600 mb-4">{podcast.description}</p>
                <div className="flex justify-between items-center text-sm text-gray-500">
                    <span>{podcast.date}</span>
                    <span>{podcast.duration}</span>
                </div>
            </div>
            <div className="px-6 py-4 bg-gray-50 border-t">
                <button
                    className="w-full flex items-center justify-center gap-2 text-blue-600 hover:text-blue-700 transition-colors"
                    aria-label={`Play ${podcast.title}`}
                >
                    <span className="text-lg">▶</span>
                    <span>Play Episode</span>
                </button>
            </div>
        </div>
    )
}