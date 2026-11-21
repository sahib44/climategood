import { ArrowLeftIcon } from '../components/icons.jsx'

// Terms and Privacy Policy. Plain-language drafts that describe what the site does today;
// they have not been reviewed by a lawyer. Keep them true: if the site starts collecting
// anything, change the Privacy Policy in the same commit.
const UPDATED = 'November 21, 2026'

function Legal({ title, children }) {
  return (
    <main className="page about">
      <h1>{title}</h1>
      <p className="muted">Last updated {UPDATED}</p>
      {children}
      <p><a className="back" href="#/"><ArrowLeftIcon /> Back to search</a></p>
    </main>
  )
}

export function Terms() {
  return (
    <Legal title="Terms">
      <h2>What Firsthand is</h2>
      <p>
        Firsthand shows public statements by candidates and elected officials, word for word, with a link to the
        original video at the moment the statement was made. It is free to use and needs no account.
      </p>
      <h2>Information, not advice or endorsement</h2>
      <ul>
        <li>Firsthand does not rate, rank, score or endorse any candidate, party or position.</li>
        <li>A quote shows what was said in one video on one date. It may not reflect a person’s full or current view.</li>
        <li>“No statement found” means only that we found none in the videos we searched. It does not imply a position.</li>
      </ul>
      <h2>Accuracy</h2>
      <p>
        Quotes are copied from the publisher’s captions or transcript and checked by code, but captions can contain
        errors and we can make mistakes. The site is provided as is, without warranties. Check the original source,
        which is linked from every quote, before relying on it.
      </p>
      <h2>Other people’s content</h2>
      <p>
        Videos, captions and transcripts belong to their publishers. Firsthand links to them and plays them in the
        publisher’s own player; it does not host or copy the video. Those sites have their own terms.
      </p>
      <h2>Corrections</h2>
      <p>
        If something is wrong, use “Report a problem” on the quote. We review reports and correct or remove entries
        that are inaccurate.
      </p>
      <h2>Changes</h2>
      <p>We may update these terms. The date at the top shows the latest version.</p>
    </Legal>
  )
}

export function Privacy() {
  return (
    <Legal title="Privacy Policy">
      <h2>What we collect</h2>
      <ul>
        <li>No accounts. We do not ask for your name, email address or any sign-in.</li>
        <li>No tracking or analytics, no advertising, and no cookies set by Firsthand.</li>
        <li>What you type in the search box is matched in your browser. It is not sent to us or stored.</li>
      </ul>
      <h2>What our host sees</h2>
      <p>
        Like any website, the company that hosts Firsthand receives technical request data such as your IP address
        and browser type when a page loads, and may keep it in short-term server logs. We do not use it to identify
        or follow visitors.
      </p>
      <h2>Videos and outside links</h2>
      <p>
        When you play a clip or open a source, you are using the publisher’s site or player (for example YouTube).
        That publisher may collect data under its own privacy policy.
      </p>
      <h2>If you report a problem</h2>
      <p>
        A report contains what you choose to write and, if you send it by email, your email address. We use it only
        to review and fix the entry.
      </p>
      <h2>Who appears on Firsthand</h2>
      <p>
        Only public figures, and only statements they made in public in their role as a candidate or official.
      </p>
      <h2>Changes</h2>
      <p>If this policy changes, we will update this page and the date at the top.</p>
    </Legal>
  )
}
