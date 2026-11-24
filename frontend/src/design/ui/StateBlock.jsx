import { useI18n } from '../../lib/i18n'
import { Button } from './Button'
import { Icon } from './Icon'

// One component for every data view's non-happy states, replacing the Stitch
// "simulate state" toggles (empty / shimmer / gateway error). Real state comes
// from the query status, never from a preview switch.

export function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-md bg-surface-container-low ${className}`} aria-hidden="true" />
}

export function LoadingBlock({ rows = 3, label }) {
  const { t } = useI18n()
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">{label || t('state.loading')}</span>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className={`h-4 ${index % 3 === 2 ? 'w-2/3' : 'w-full'}`} />
      ))}
    </div>
  )
}

export function EmptyBlock({ icon = 'inbox', title, children, action }) {
  const { t } = useI18n()
  return (
    <div className="flex flex-col items-center px-6 py-10 text-center">
      <span className="grid h-14 w-14 place-items-center rounded-full bg-primary-tint text-primary">
        <Icon name={icon} size={28} />
      </span>
      <h3 className="mt-4 text-title-md text-ink">{title || t('state.empty_title')}</h3>
      {children && <div className="mt-1 max-w-md text-body-sm text-ink-2">{children}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function ErrorBlock({ error, onRetry, title }) {
  const { t } = useI18n()
  const offline = error?.status === 0
  return (
    <div role="alert" className="flex flex-col items-center px-6 py-10 text-center">
      <span className="grid h-14 w-14 place-items-center rounded-full bg-risk-high-bg text-risk-high-ink">
        <Icon name={offline ? 'cloud_off' : 'error'} size={28} />
      </span>
      <h3 className="mt-4 text-title-md text-ink">
        {title || (offline ? t('state.offline_title') : t('state.error_title'))}
      </h3>
      {error?.message && <p className="mt-1 max-w-md text-body-sm text-ink-2">{error.message}</p>}
      {onRetry && (
        <Button variant="ghost" size="sm" icon="refresh" className="mt-5" onClick={onRetry}>
          {t('state.retry')}
        </Button>
      )}
    </div>
  )
}

/**
 * Render the right block for a TanStack Query result.
 *   <StateBlock query={q} isEmpty={(d) => !d.cases.length} empty={<EmptyBlock …/>}>
 *     {(data) => <Table rows={data.cases} />}
 *   </StateBlock>
 */
export function StateBlock({ query, isEmpty, empty, loadingRows = 3, children }) {
  if (query.isPending) return <LoadingBlock rows={loadingRows} />
  if (query.isError) return <ErrorBlock error={query.error} onRetry={() => query.refetch()} />
  if (isEmpty?.(query.data)) return empty || <EmptyBlock />
  return children(query.data)
}
