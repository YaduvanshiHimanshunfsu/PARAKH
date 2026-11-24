import { NavLink, Outlet, Link } from 'react-router-dom'
import { useI18n } from '../lib/i18n'
import { Icon } from '../design/ui'
import { Brand } from './Brand'

// Citizen shell from the Stitch citizen screens: top nav on desktop, bottom tab
// bar on phones (< 768 px), EN/हिंदी toggle and the 1930 emergency pill on both.

const TOP_LINKS = [
  ['/check', 'nav.check', 'जाँचें'],
  ['/apk', 'nav.apk', 'ऐप जाँच'],
  ['/learn', 'nav.learn', 'सीखें'],
  ['/evidence', 'nav.evidence', 'साक्ष्य'],
  ['/help', 'nav.help', 'सहायता'],
  ['/rescue', 'nav.rescue', 'संकट सहायता'],
]

const TAB_LINKS = [
  ['/', 'nav.home', 'home', true],
  ['/check', 'nav.check', 'search_check', false],
  ['/apk', 'nav.apk', 'android', false],
  ['/learn', 'nav.learn', 'school', false],
  ['/rescue', 'nav.rescue', 'emergency', false],
]

export function LanguageToggle() {
  const { lang, setLang, t } = useI18n()
  return (
    <div role="group" aria-label={t('nav.language')} className="flex rounded-chip border border-line bg-card p-0.5 text-body-sm font-semibold">
      {[
        ['en', 'EN'],
        ['hi', 'हिं'],
      ].map(([code, label]) => (
        <button
          key={code}
          type="button"
          onClick={() => setLang(code)}
          aria-pressed={lang === code}
          className={`h-8 rounded-lg px-2.5 ${lang === code ? 'bg-primary text-white' : 'text-ink-2 hover:text-primary'}`}
          lang={code}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

export function HelplinePill({ compact = false }) {
  const { t } = useI18n()
  return (
    <a
      href="tel:1930"
      aria-label={t('nav.helpline_label')}
      className="inline-flex h-9 items-center gap-1.5 rounded-full bg-risk-high-ink px-3 text-body-sm font-bold text-white hover:bg-[#991b1b]"
    >
      <Icon name="call" filled size={18} />
      {compact ? '1930' : t('nav.helpline')}
    </a>
  )
}

export function CitizenLayout() {
  const { t } = useI18n()
  return (
    <div className="flex min-h-screen flex-col bg-canvas pb-[calc(4.5rem+env(safe-area-inset-bottom))] md:pb-0">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2">
        Skip to content
      </a>
      <header className="glass sticky top-0 z-40 border-x-0 border-t-0">
        <div className="mx-auto flex max-w-[1280px] items-center gap-3 px-4 py-3 md:px-8">
          <Brand subtitle={t('brand.citizen_sub')} />
          <nav aria-label={t('nav.main')} className="ml-6 hidden flex-1 items-center gap-1 lg:flex">
            {TOP_LINKS.map(([to, key, hindi]) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `rounded-chip px-3 py-1.5 text-body-sm font-semibold leading-tight ${
                    isActive ? 'bg-primary-tint text-primary' : 'text-ink-2 hover:text-primary'
                  }`
                }
              >
                {t(key)}
                <span className="hi block text-[11px] font-medium text-ink-3" lang="hi">
                  {hindi}
                </span>
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <LanguageToggle />
            <span className="hidden sm:inline-flex">
              <HelplinePill />
            </span>
            <span className="sm:hidden">
              <HelplinePill compact />
            </span>
            <Link
              to="/investigate/login"
              className="hidden items-center gap-1 rounded-chip px-2 py-1.5 text-body-sm font-semibold text-ink-2 hover:text-primary md:inline-flex"
            >
              <Icon name="badge" size={18} />
              {t('nav.officer_login')}
            </Link>
          </div>
        </div>
      </header>

      <main id="main" className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-line bg-card">
        <div className="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-3 px-4 py-6 text-body-sm text-ink-2 md:px-8">
          <p className="max-w-2xl">{t('footer.disclaimer')}</p>
          <div className="flex items-center gap-4">
            <Link to="/privacy" className="hover:text-primary">
              {t('footer.privacy')}
            </Link>
            <a href="https://cybercrime.gov.in" target="_blank" rel="noreferrer" className="hover:text-primary">
              cybercrime.gov.in
            </a>
          </div>
        </div>
      </footer>

      <nav
        aria-label={t('nav.mobile')}
        className="glass fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-x-0 border-b-0 pb-[env(safe-area-inset-bottom)] md:hidden"
      >
        {TAB_LINKS.map(([to, key, icon, end]) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 py-2 text-[11px] font-semibold ${isActive ? 'text-primary' : 'text-ink-2'}`
            }
          >
            <Icon name={icon} size={22} />
            {t(key)}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
