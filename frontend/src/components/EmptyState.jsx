import { DocIcon } from './icons.jsx'

// Rule 7: say what we searched and offer a neutral question. Never imply a position from silence.
export default function EmptyState({ result }) {
  const n = result.coverage.videos_searched
  const message =
    result.empty_state?.message || `No statement found in the ${n} video${n === 1 ? '' : 's'} we searched.`
  const question = result.empty_state?.suggested_question || result.topic.suggested_question
  return (
    <div className="empty">
      <DocIcon />
      <div>
        <p className="empty-title">{message}</p>
        <p className="muted">You could ask their office: {question}</p>
      </div>
    </div>
  )
}
