// Material Symbols Outlined (self-hosted via the `material-symbols` package).
// Decorative by default; pass `label` when the icon is the only content.

export function Icon({ name, label, filled = false, className = '', size }) {
  const style = {}
  if (filled) style.fontVariationSettings = "'FILL' 1"
  if (size) style.fontSize = typeof size === 'number' ? `${size}px` : size
  return (
    <span
      className={`material-symbols-outlined ${className}`}
      style={style}
      aria-hidden={label ? undefined : true}
      role={label ? 'img' : undefined}
      aria-label={label}
    >
      {name}
    </span>
  )
}
