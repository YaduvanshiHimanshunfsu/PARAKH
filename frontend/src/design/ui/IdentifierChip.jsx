import { useState } from 'react'
import { Link } from 'react-router-dom'
import { identifierMeta } from '../vocab'
import { Icon } from './Icon'

// Forensic identifier chip (DESIGN.md §Components 3): 10% tint of the type
// colour, mono value, copy-to-clipboard. Several identifier colours (e.g. the
// domain teal #0D9488) are under 4.5:1 as 12px text, so the text colour is
// mixed 30% toward ink; the pure token colour stays on the border and icon.

export function IdentifierChip({ type, value, count, to, copy = true, className = '' }) {
  const meta = identifierMeta(type)
  const [copied, setCopied] = useState(false)
  const style = {
    background: `color-mix(in srgb, ${meta.color} 10%, white)`,
    borderColor: `color-mix(in srgb, ${meta.color} 35%, white)`,
    color: `color-mix(in srgb, ${meta.color} 70%, #0f172a)`,
  }

  async function handleCopy(event) {
    event.preventDefault()
    event.stopPropagation()
    try {
      await navigator.clipboard?.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard blocked: nothing to do */
    }
  }

  const body = (
    <>
      <span style={{ color: meta.color }} className="inline-flex">
        <Icon name={meta.icon} size={15} />
      </span>
      <span className="text-label-ui uppercase opacity-80">{meta.label}</span>
      <span className="text-mono-sm max-w-[22rem] truncate">{value}</span>
      {typeof count === 'number' && (
        <span className="text-mono-sm rounded-full bg-white/70 px-1.5 tnum">×{count}</span>
      )}
    </>
  )

  return (
    <span
      className={`inline-flex h-7 max-w-full items-center gap-1.5 rounded-chip border px-2.5 ${className}`}
      style={style}
      title={value}
    >
      {to ? (
        <Link to={to} className="inline-flex min-w-0 items-center gap-1.5 hover:underline">
          {body}
        </Link>
      ) : (
        body
      )}
      {copy && (
        <button
          type="button"
          onClick={handleCopy}
          className="-mr-1 grid h-6 w-6 place-items-center rounded-md hover:bg-white/80"
          aria-label={copied ? `${meta.label} copied` : `Copy ${meta.label} ${value}`}
        >
          <Icon name={copied ? 'check' : 'content_copy'} size={14} />
        </button>
      )}
    </span>
  )
}
