import { useRef, useState } from 'react'
import { Pause, Play } from 'lucide-react'
import { podcastAudioUrl } from '../lib/api'

function formatDuration(duration) {
  const [hours, minutes, seconds] = duration.split(':').map(Number)
  return `${hours * 60 + minutes} min ${seconds} s`
}

export default function PodcastRow({ podcast }) {
  const audio = useRef(null)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)

  return (
    <div className="rounded-2xl border border-line bg-panel p-3.5">
      <div className="flex items-center gap-3.5">
        <button
          className="grid size-11 flex-none place-items-center rounded-full bg-cheese text-ink"
          aria-label={playing ? `Pause ${podcast.title}` : `Play ${podcast.title}`}
          onClick={() => (playing ? audio.current.pause() : audio.current.play())}
        >
          {playing ? <Pause size={18} /> : <Play size={18} />}
        </button>
        <div className="min-w-0">
          <h3 className="text-lg font-bold">{podcast.title}</h3>
          <p className="text-sm text-muted">{formatDuration(podcast.duration)}</p>
        </div>
      </div>
      {progress > 0 && (
        <div className="mt-3 h-1.5 rounded-full bg-line">
          <div className="h-full rounded-full bg-cheese" style={{ width: `${progress}%` }} />
        </div>
      )}
      <audio
        ref={audio}
        src={podcastAudioUrl(podcast.audio)}
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onTimeUpdate={(event) => {
          const { currentTime, duration } = event.target
          setProgress(duration ? (currentTime / duration) * 100 : 0)
        }}
      />
    </div>
  )
}
