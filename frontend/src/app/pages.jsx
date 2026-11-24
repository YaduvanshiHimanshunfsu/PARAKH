import { useI18n } from '../lib/i18n'
import { ButtonLink, Card, Icon } from '../design/ui'

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
