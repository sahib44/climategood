import { ArrowLeftIcon } from '../components/icons.jsx'

export default function About({ data }) {
  return (
    <main className="page about">
      <h1>How Firsthand works</h1>
      <p>
        Firsthand shows what a candidate actually said, word for word, about specific climate issues, with a link
        that starts at the moment they said it. It shows evidence, or it says no statement was found. It never judges.
      </p>
      <h2>How we verified</h2>
      <ul>
        <li>Every quote is copied from the publisher’s official captions or transcript, and checked against it by code. Quotes are never written or summarized by AI.</li>
        <li>Every match for a topic is shown, oldest first, with what was said before and after. We never pick “best” quotes.</li>
        <li>Each candidate’s page says how many videos and hours we searched. Fewer results can mean less coverage, not a different position.</li>
        <li>Numbers and claims are labeled <em>measured</em>, <em>modeled</em> or <em>assumed</em>. A verified quote is measured. Filing a quote under a topic is modeled.</li>
      </ul>
      {data?.unevenness_warning && (
        <>
          <h2>Coverage right now</h2>
          <p>{data.unevenness_warning}</p>
        </>
      )}
      <h2>What we don’t do</h2>
      <ul>
        <li>No scores, ratings, rankings or endorsements.</li>
        <li>No accounts, no tracking, no analytics. Your searches stay in your browser.</li>
        <li>No re-hosted video. Clips play on the original publisher’s site.</li>
      </ul>
      <p><a className="back" href="#/"><ArrowLeftIcon /> Back to search</a></p>
    </main>
  )
}
