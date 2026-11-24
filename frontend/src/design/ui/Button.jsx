import { Link } from 'react-router-dom'
import { Icon } from './Icon'

// Variants from DESIGN.md §Components 1:
//   primary — police blue action        citizen — sandstone/saffron highlight
//   ghost   — white secondary           danger  — emergency (1930, report)
const VARIANTS = {
  primary: 'bg-primary text-white hover:bg-primary-hover border border-primary',
  citizen: 'bg-accent-strong text-white hover:bg-[#9a3412] border border-accent-strong',
  ghost: 'bg-card text-ink border border-line hover:bg-canvas hover:text-primary',
  danger: 'bg-risk-high-ink text-white hover:bg-[#991b1b] border border-risk-high-ink',
  subtle: 'bg-primary-tint text-primary border border-transparent hover:bg-surface-container',
}

const SIZES = {
  sm: 'h-9 px-3 text-body-sm gap-1.5',
  md: 'h-11 px-4 text-title-md gap-2',
  lg: 'h-[52px] px-6 text-title-md gap-2',
}

export function buttonClasses({ variant = 'primary', size = 'md', block = false, className = '' } = {}) {
  return [
    'inline-flex items-center justify-center rounded-chip font-semibold whitespace-nowrap',
    'transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50',
    VARIANTS[variant] || VARIANTS.primary,
    SIZES[size] || SIZES.md,
    block ? 'w-full' : '',
    className,
  ].join(' ')
}

export function Button({ variant, size, block, icon, iconRight, className, children, type = 'button', loading = false, ...rest }) {
  return (
    <button
      type={type}
      className={buttonClasses({ variant, size, block, className })}
      disabled={loading || rest.disabled}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Icon name="progress_activity" className="animate-spin" /> : icon && <Icon name={icon} />}
      {children}
      {iconRight && <Icon name={iconRight} />}
    </button>
  )
}

/** Router link styled as a button. `href` (e.g. tel:1930) renders a plain anchor. */
export function ButtonLink({ to, href, variant, size, block, icon, iconRight, className, children, ...rest }) {
  const classes = buttonClasses({ variant, size, block, className })
  const content = (
    <>
      {icon && <Icon name={icon} />}
      {children}
      {iconRight && <Icon name={iconRight} />}
    </>
  )
  if (href) {
    return (
      <a href={href} className={classes} {...rest}>
        {content}
      </a>
    )
  }
  return (
    <Link to={to} className={classes} {...rest}>
      {content}
    </Link>
  )
}
