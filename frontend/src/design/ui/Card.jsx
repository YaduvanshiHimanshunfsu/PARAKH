// Cards per DESIGN.md elevation levels.
//   card  — level 1, white, 1px line, 16px radius
//   glass — level 2, frosted
//   hero  — 24px radius panel for verdict banners and citizen guidance
//   sand  — warm civic band

const TONES = {
  card: 'bg-card border border-line shadow-l1 rounded-card',
  glass: 'glass shadow-l2 rounded-card',
  hero: 'bg-card border border-line shadow-l2 rounded-hero',
  sand: 'bg-sand border border-line-soft rounded-card',
  plain: 'rounded-card',
}

export function Card({ as: Tag = 'section', tone = 'card', className = '', children, ...rest }) {
  return (
    <Tag className={`${TONES[tone] || TONES.card} ${className}`} {...rest}>
      {children}
    </Tag>
  )
}

/** Section heading with an optional Hindi line and right-side action. */
export function CardHeader({ title, hindi, eyebrow, action, className = '' }) {
  return (
    <header className={`flex flex-wrap items-start justify-between gap-3 ${className}`}>
      <div className="min-w-0">
        {eyebrow && <p className="text-label-ui uppercase text-accent-strong">{eyebrow}</p>}
        <h2 className="text-headline-sm text-ink">{title}</h2>
        {hindi && (
          <p className="hi text-body-sm text-ink-2" lang="hi">
            {hindi}
          </p>
        )}
      </div>
      {action}
    </header>
  )
}
