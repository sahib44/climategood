const base = {
  width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
  strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true,
}

export const SearchIcon = () => (
  <svg {...base}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
)
export const PlayIcon = () => (
  <svg {...base} fill="currentColor" stroke="none"><path d="M8 5.5v13l11-6.5z" /></svg>
)
export const CheckIcon = () => (
  <svg {...base}><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>
)
export const VideoIcon = () => (
  <svg {...base}><rect x="3" y="6" width="13" height="12" rx="2" /><path d="m16 10 5-3v10l-5-3" /></svg>
)
export const DocIcon = () => (
  <svg {...base} width="22" height="22"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5M9 13h6M9 17h6" /></svg>
)
