// Every icon comes from an Iconify icon set (https://icon-sets.iconify.design), per AGENTS.md.
// These are from the Lucide set. The SVG is copied in, with its Iconify id beside it, so
// nothing is fetched from a third party when a voter loads the page (rule 10).
// To add one: find it on icon-sets.iconify.design, copy its SVG body here, name the id.

const Icon = ({ size = 16, children }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {children}
  </svg>
)

// lucide:search
export const SearchIcon = () => <Icon><path d="m21 21l-4.34-4.34" /><circle cx="11" cy="11" r="8" /></Icon>
// lucide:play
export const PlayIcon = () => (
  <Icon><path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z" /></Icon>
)
// lucide:check
export const CheckIcon = () => <Icon><path d="M20 6L9 17l-5-5" /></Icon>
// lucide:video
export const VideoIcon = () => (
  <Icon>
    <path d="m16 13l5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5" />
    <rect width="14" height="12" x="2" y="6" rx="2" />
  </Icon>
)
// lucide:file-text
export const DocIcon = () => (
  <Icon size={22}>
    <path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z" />
    <path d="M14 2v5a1 1 0 0 0 1 1h5M10 9H8m8 4H8m8 4H8" />
  </Icon>
)
// lucide:arrow-left
export const ArrowLeftIcon = () => <Icon><path d="m12 19l-7-7l7-7m7 7H5" /></Icon>
// lucide:arrow-up-right
export const ArrowUpRightIcon = () => <Icon size={14}><path d="M7 7h10v10M7 17L17 7" /></Icon>
