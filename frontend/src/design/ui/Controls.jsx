import { useId, useRef, useState } from 'react'
import { Icon } from './Icon'

/**
 * Segmented control / mode picker (check modes, period filters).
 * Implemented as a radio group so arrow keys and screen readers work.
 */
export function Segmented({ label, options, value, onChange, size = 'md', className = '' }) {
  const name = useId()
  const pad = size === 'sm' ? 'h-8 px-3 text-body-sm' : 'h-10 px-3.5 text-body-sm sm:text-body-md'
  return (
    <fieldset className={`min-w-0 ${className}`}>
      <legend className="sr-only">{label}</legend>
      <div className="flex max-w-full gap-1 overflow-x-auto rounded-chip border border-line bg-card p-1">
        {options.map((option) => {
          const checked = option.value === value
          return (
            <label
              key={option.value}
              className={`inline-flex shrink-0 cursor-pointer items-center gap-1.5 rounded-lg font-semibold transition-colors ${pad} ${
                checked ? 'bg-primary text-white' : 'text-ink-2 hover:bg-canvas hover:text-primary'
              } has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-primary`}
            >
              <input
                type="radio"
                name={name}
                value={option.value}
                checked={checked}
                onChange={() => onChange(option.value)}
                className="sr-only"
              />
              {option.icon && <Icon name={option.icon} size={18} />}
              <span>{option.label}</span>
              {option.hindi && (
                <span className={`hi hidden md:inline ${checked ? 'text-white/85' : 'text-ink-3'}`} lang="hi">
                  {option.hindi}
                </span>
              )}
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}

/** Explicit-consent checkbox. Always unchecked by default (ADR-001). */
export function ConsentCheckbox({ checked, onChange, children, hindi }) {
  const id = useId()
  return (
    <div className="flex items-start gap-3 rounded-chip border border-line bg-canvas p-3">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-0.5 h-5 w-5 shrink-0 accent-[#1d4ed8]"
      />
      <label htmlFor={id} className="text-body-sm text-ink">
        {children}
        {hindi && (
          <span className="hi mt-0.5 block text-ink-2" lang="hi">
            {hindi}
          </span>
        )}
      </label>
    </div>
  )
}

/** Drag-and-drop file picker with a real <input type=file> underneath. */
export function FileDrop({ accept, onFile, title, hint, icon = 'upload_file', disabled = false }) {
  const inputRef = useRef(null)
  const id = useId()
  const [dragging, setDragging] = useState(false)

  function pick(files) {
    const file = files?.[0]
    if (file && !disabled) onFile(file)
  }

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        pick(event.dataTransfer.files)
      }}
      className={`flex flex-col items-center rounded-card border-2 border-dashed px-6 py-10 text-center transition-colors ${
        dragging ? 'border-primary bg-primary-tint' : 'border-outline-variant bg-card'
      }`}
    >
      <span className="grid h-14 w-14 place-items-center rounded-2xl bg-primary-tint text-primary">
        <Icon name={icon} size={28} />
      </span>
      <p className="mt-4 text-title-md text-ink">{title}</p>
      {hint && <p className="mt-1 text-body-sm text-ink-2">{hint}</p>}
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept={accept}
        disabled={disabled}
        onChange={(event) => {
          pick(event.target.files)
          event.target.value = ''
        }}
        className="sr-only"
      />
      <label
        htmlFor={id}
        className="mt-5 inline-flex h-11 cursor-pointer items-center gap-2 rounded-chip bg-primary px-4 text-title-md text-white hover:bg-primary-hover"
      >
        <Icon name="folder_open" /> Choose file
      </label>
    </div>
  )
}

/**
 * Horizontal pipeline stepper (analysing screen, ingestion, case status).
 * steps: [{label, hindi?, status: 'done'|'current'|'todo'}]
 */
export function Stepper({ steps, label = 'Progress' }) {
  return (
    <ol aria-label={label} className="flex flex-wrap items-start gap-y-4">
      {steps.map((step, index) => {
        const done = step.status === 'done'
        const current = step.status === 'current'
        return (
          <li
            key={step.label}
            className="flex min-w-[7rem] flex-1 flex-col items-center text-center"
            aria-current={current ? 'step' : undefined}
          >
            <div className="flex w-full items-center">
              <span className={`h-0.5 flex-1 ${index === 0 ? 'invisible' : done || current ? 'bg-primary' : 'bg-line'}`} />
              <span
                className={`grid h-9 w-9 shrink-0 place-items-center rounded-full border-2 ${
                  done
                    ? 'border-risk-low bg-risk-low text-white'
                    : current
                      ? 'border-primary bg-white text-primary ring-4 ring-primary-tint'
                      : 'border-line bg-white text-ink-3'
                }`}
              >
                {done ? <Icon name="check" size={18} /> : <span className="text-body-sm font-bold">{index + 1}</span>}
              </span>
              <span className={`h-0.5 flex-1 ${index === steps.length - 1 ? 'invisible' : done ? 'bg-primary' : 'bg-line'}`} />
            </div>
            <span className={`mt-2 text-body-sm font-semibold ${current ? 'text-primary' : 'text-ink'}`}>{step.label}</span>
            {step.hindi && (
              <span className="hi text-body-sm text-ink-3" lang="hi">
                {step.hindi}
              </span>
            )}
          </li>
        )
      })}
    </ol>
  )
}

/**
 * Vertical timeline (campaign evolution, audit trail, rescue checklist).
 * items: [{id, time, title, body?, tone?: 'default'|'high'|'low'|'primary'}]
 */
export function Timeline({ items, label = 'Timeline' }) {
  const dot = {
    default: 'bg-ink-3',
    primary: 'bg-primary',
    high: 'bg-risk-high',
    low: 'bg-risk-low',
    medium: 'bg-risk-medium',
  }
  return (
    <ol aria-label={label} className="relative ml-2 border-l-2 border-line pl-5">
      {items.map((item) => (
        <li key={item.id} className="relative pb-5 last:pb-0">
          <span className={`absolute -left-[27px] top-1.5 h-3 w-3 rounded-full ring-4 ring-white ${dot[item.tone] || dot.default}`} />
          {item.time && <p className="text-mono-sm text-ink-3 tnum">{item.time}</p>}
          <p className="text-body-md font-semibold text-ink">{item.title}</p>
          {item.body && <div className="text-body-sm text-ink-2">{item.body}</div>}
        </li>
      ))}
    </ol>
  )
}
