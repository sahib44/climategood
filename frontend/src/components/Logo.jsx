// The Firsthand mark: an open hand in the site's pixel style.
// It is the brand mark, not a UI icon, so it is drawn here rather than taken from Iconify.
// The hand takes the text color (set in styles.css), so it works on white pages, on the
// landing scene by day and by night, and on the ink hover chip. public/logo.svg and
// public/favicon.svg are the same shape as files.
export default function Logo({ size = 22 }) {
  return (
    <svg className="logo" width={size} height={size} viewBox="0 0 16 16" shapeRendering="crispEdges" aria-hidden="true">
      <path fill="currentColor" d="M6 0h2v1h-2zM3 1h2v1h-2zM6 1h2v1h-2zM9 1h2v1h-2zM3 2h2v1h-2zM6 2h2v1h-2zM9 2h2v1h-2zM12 2h2v1h-2zM3 3h2v1h-2zM6 3h2v1h-2zM9 3h2v1h-2zM12 3h2v1h-2zM3 4h2v1h-2zM6 4h2v1h-2zM9 4h2v1h-2zM12 4h2v1h-2zM3 5h2v1h-2zM6 5h2v1h-2zM9 5h2v1h-2zM12 5h2v1h-2zM3 6h11v1h-11zM0 7h2v1h-2zM3 7h11v1h-11zM0 8h2v1h-2zM3 8h11v1h-11zM0 9h14v1h-14zM0 10h14v1h-14zM1 11h13v1h-13zM2 12h12v1h-12zM3 13h10v1h-10zM4 14h8v1h-8zM4 15h8v1h-8z" />
    </svg>
  )
}

// The wordmark: "First" is drawn on a pixel grid (15 cells to the em, stems two cells wide) in
// the proportions of Newsreader at weight 600, so it echoes the scene and the hand and sits
// on the same baseline as "hand", which is the live font.
export function Wordmark() {
  return (
    <span className="wordmark" role="img" aria-label="Firsthand">
      <svg viewBox="0 0 33 11" shapeRendering="crispEdges" aria-hidden="true">
        <path fill="currentColor" d="M0 0h7v1h-7zM9 0h2v1h-2zM1 1h2v1h-2zM6 1h1v1h-1zM9 1h2v1h-2zM1 2h2v1h-2zM28 2h2v1h-2zM1 3h2v1h-2zM5 3h1v1h-1zM28 3h2v1h-2zM1 4h5v1h-5zM8 4h3v1h-3zM13 4h3v1h-3zM17 4h2v1h-2zM21 4h4v1h-4zM27 4h5v1h-5zM1 5h2v1h-2zM5 5h1v1h-1zM9 5h2v1h-2zM14 5h4v1h-4zM20 5h2v1h-2zM24 5h2v1h-2zM28 5h2v1h-2zM1 6h2v1h-2zM9 6h2v1h-2zM14 6h2v1h-2zM20 6h2v1h-2zM28 6h2v1h-2zM1 7h2v1h-2zM9 7h2v1h-2zM14 7h2v1h-2zM21 7h3v1h-3zM28 7h2v1h-2zM1 8h2v1h-2zM9 8h2v1h-2zM14 8h2v1h-2zM23 8h3v1h-3zM28 8h2v1h-2zM1 9h2v1h-2zM9 9h2v1h-2zM14 9h2v1h-2zM20 9h2v1h-2zM24 9h2v1h-2zM28 9h2v1h-2zM31 9h1v1h-1zM0 10h4v1h-4zM8 10h4v1h-4zM13 10h4v1h-4zM21 10h4v1h-4zM29 10h3v1h-3z" />
      </svg>
      <span aria-hidden="true">hand</span>
    </span>
  )
}
