/**
 * The PARAKH mark: a geometric "P" whose counter is a true circle, so the
 * bowl reads as a lens. "परख" means to examine or to assay, and examining is
 * what the product does — the mark says that rather than claiming authority.
 *
 * Deliberately not a shield, a crest or any state emblem (H.1): PARAKH is a
 * tool the police use, not an insignia they wear.
 *
 * Drawn on a 32x32 grid as a single even-odd path, so it renders correctly in
 * one flat colour. That matters because the same mark has to survive a 16px
 * favicon, a monochrome print header, and a fax-quality scan of a requisition.
 */
export function ParakhMark({ size = 22, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M8.6 4.4h9.6a8.1 8.1 0 0 1 0 16.2h-4.1v6.9a.5.5 0 0 1-.5.5H8.6a.5.5 0 0 1-.5-.5V4.9a.5.5 0 0 1 .5-.5Zm13.3 8.1a3.7 3.7 0 1 0-7.4 0 3.7 3.7 0 0 0 7.4 0Z"
        fill="currentColor"
      />
    </svg>
  )
}
