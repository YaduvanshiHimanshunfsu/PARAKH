import { useI18n } from '../lib/i18n'
import { ButtonLink, Card, Icon } from '../design/ui'

/** Honest placeholder for routes whose screen is not built yet. */
export function WorkInProgress({ title, phase, source }) {
  const { t } = useI18n()
  return (
    <div className="mx-auto max-w-[1280px] px-4 py-10 md:px-8">
      <Card className="p-5 md:p-8">
        <div className="flex items-start gap-4">
          <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-primary-tint text-primary">
            <Icon name="construction" size={26} />
          </span>
          <div className="min-w-0">
            <p className="text-label-ui uppercase text-accent-strong">{t('wip.title')}</p>
            <h1 className="mt-1 text-headline-md">{title}</h1>
            <p className="mt-2 max-w-2xl text-body-md text-ink-2 [overflow-wrap:anywhere]">{t('wip.body', { phase, source })}</p>
          </div>
        </div>
      </Card>
    </div>
  )
}

export function NotFound() {
  const { t } = useI18n()
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-4 py-20 text-center">
      <span className="grid h-16 w-16 place-items-center rounded-full bg-primary-tint text-primary">
        <Icon name="travel_explore" size={32} />
      </span>
      <h1 className="mt-5 text-headline-md">{t('notfound.title')}</h1>
      <p className="mt-2 text-body-md text-ink-2">{t('notfound.body')}</p>
      <ButtonLink to="/" className="mt-6" icon="home">
        {t('notfound.home')}
      </ButtonLink>
    </div>
  )
}
