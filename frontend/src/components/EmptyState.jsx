import { DocIcon } from './icons.jsx'

// Rule 7: say what we searched and offer a neutral question. Never imply a position from silence.
export default function EmptyState({ result, topic }) {
  const n = result.coverage.videos_searched
  // With nothing searched, "no statement found" would wrongly suggest we looked. Say we have not.
  const message =
    n === 0
      ? 'We have not searched any videos for this candidate yet.'
      : result.empty_state?.message || `No statement found in the ${n} video${n === 1 ? '' : 's'} we searched.`
  const question = result.empty_state?.suggested_question || result.topic.suggested_question
  return (
    <div className="empty">
      <DocIcon />
      <div>
        <p className="empty-title">{topic ? `${topic.label}: ` : ''}{message}</p>
        <p className="muted">You could ask their office: {question}</p>
      </div>
    </div>
  )
}
