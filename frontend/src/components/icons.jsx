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
export const SearchIcon = () => <Icon><path d="m21 21l-4.34-4.34"/><circle cx="11" cy="11" r="8"/></Icon>
// lucide:play
export const PlayIcon = () => <Icon><path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"/></Icon>
// lucide:video
export const VideoIcon = () => <Icon><path d="m16 13l5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5"/><rect width="14" height="12" x="2" y="6" rx="2"/></Icon>
// lucide:file-text
export const DocIcon = () => <Icon size={22}><path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"/><path d="M14 2v5a1 1 0 0 0 1 1h5M10 9H8m8 4H8m8 4H8"/></Icon>
// lucide:arrow-left
export const ArrowLeftIcon = () => <Icon><path d="m12 19l-7-7l7-7m7 7H5"/></Icon>
// lucide:arrow-up-right
export const ArrowUpRightIcon = () => <Icon size={14}><path d="M7 7h10v10M7 17L17 7"/></Icon>
// lucide:briefcase
export const BriefcaseIcon = () => <Icon size={14}><path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/><rect width="20" height="14" x="2" y="6" rx="2"/></Icon>
// lucide:flag
export const FlagIcon = () => <Icon size={14}><path d="M4 22V4a1 1 0 0 1 .4-.8A6 6 0 0 1 8 2c3 0 5 2 7.333 2q2 0 3.067-.8A1 1 0 0 1 20 4v10a1 1 0 0 1-.4.8A6 6 0 0 1 16 16c-3 0-5-2-8-2a6 6 0 0 0-4 1.528"/></Icon>
// lucide:chevron-down
export const ChevronIcon = () => <Icon><path d="m6 9l6 6l6-6"/></Icon>
// lucide:info
export const InfoIcon = () => <Icon><circle cx="12" cy="12" r="10"/><path d="M12 16v-4m0-4h.01"/></Icon>

// One icon per topic in config/topics.json, so a topic looks the same wherever it appears.
const TOPIC_ICONS = {
  // lucide:zap
  clean_power_requirement: <><path d="M15.914 4a1.5 1.5 0 0 0-2.474-1.561l-9 9A1.5 1.5 0 0 0 5.5 14h4.002a.5.5 0 0 1 .471.666L8.086 20a1.5 1.5 0 0 0 2.475 1.56l9-9A1.5 1.5 0 0 0 18.5 10h-3.997a.5.5 0 0 1-.472-.667z"/></>,
  // lucide:shield
  ratepayer_protection: <><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/></>,
  // lucide:droplet
  water_energy_disclosure: <><path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5S5 13 5 15a7 7 0 0 0 7 7"/></>,
  // lucide:circle-pause
  moratorium: <><circle cx="12" cy="12" r="10"/><path d="M10 15V9m4 6V9"/></>,
  // lucide:users
  local_approval: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 3.128a4 4 0 0 1 0 7.744M22 21v-2a4 4 0 0 0-3-3.87"/><circle cx="9" cy="7" r="4"/></>,
}
// lucide:file-text for a topic added later without its own icon.
const TOPIC_FALLBACK = <><path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"/><path d="M14 2v5a1 1 0 0 0 1 1h5M10 9H8m8 4H8m8 4H8"/></>
export const TopicIcon = ({ id, size = 20 }) => <Icon size={size}>{TOPIC_ICONS[id] || TOPIC_FALLBACK}</Icon>
