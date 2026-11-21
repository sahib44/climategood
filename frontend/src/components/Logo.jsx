// The Firsthand mark: an open hand in the site's pixel style.
// It is the brand mark, not a UI icon, so it is drawn here rather than taken from Iconify.
// The hand takes the text color (set in styles.css), so it works on white pages, on the
// landing scene by day and by night, and on the ink hover chip. public/logo.svg and
// public/favicon.svg are the same shape as files.
export default function Logo() {
  return (
    <svg className="logo" viewBox="0 0 16 16" shapeRendering="crispEdges" aria-hidden="true">
      <path fill="currentColor" d="M6 0h2v1h-2zM3 1h2v1h-2zM6 1h2v1h-2zM9 1h2v1h-2zM3 2h2v1h-2zM6 2h2v1h-2zM9 2h2v1h-2zM12 2h2v1h-2zM3 3h2v1h-2zM6 3h2v1h-2zM9 3h2v1h-2zM12 3h2v1h-2zM3 4h2v1h-2zM6 4h2v1h-2zM9 4h2v1h-2zM12 4h2v1h-2zM3 5h2v1h-2zM6 5h2v1h-2zM9 5h2v1h-2zM12 5h2v1h-2zM3 6h11v1h-11zM0 7h2v1h-2zM3 7h11v1h-11zM0 8h2v1h-2zM3 8h11v1h-11zM0 9h14v1h-14zM0 10h14v1h-14zM1 11h13v1h-13zM2 12h12v1h-12zM3 13h10v1h-10zM4 14h8v1h-8zM4 15h8v1h-8z" />
    </svg>
  )
}

// The wordmark: "First" is drawn on a pixel grid (8 cells tall, stems two cells wide) at
// the cap height of Newsreader, so it echoes the scene and the hand and sits
// on the same baseline as "hand", which is the live font.
export function Wordmark() {
  return (
    <span className="wordmark" role="img" aria-label="Firsthand">
      <svg viewBox="0 0 27 8" shapeRendering="crispEdges" aria-hidden="true">
        <path fill="currentColor" d="M0 0h6v1h-6zM7 0h2v1h-2zM23 0h2v1h-2zM0 1h2v1h-2zM5 1h1v1h-1zM23 1h2v1h-2zM0 2h2v1h-2zM7 2h2v1h-2zM10 2h2v1h-2zM13 2h2v1h-2zM17 2h4v1h-4zM22 2h4v1h-4zM0 3h5v1h-5zM7 3h2v1h-2zM10 3h4v1h-4zM16 3h2v1h-2zM23 3h2v1h-2zM0 4h2v1h-2zM7 4h2v1h-2zM10 4h2v1h-2zM17 4h3v1h-3zM23 4h2v1h-2zM0 5h2v1h-2zM7 5h2v1h-2zM10 5h2v1h-2zM19 5h2v1h-2zM23 5h2v1h-2zM0 6h2v1h-2zM7 6h2v1h-2zM10 6h2v1h-2zM19 6h2v1h-2zM23 6h2v1h-2zM0 7h4v1h-4zM7 7h2v1h-2zM10 7h2v1h-2zM16 7h4v1h-4zM24 7h2v1h-2z" />
      </svg>
      <span aria-hidden="true">hand</span>
    </span>
  )
}
