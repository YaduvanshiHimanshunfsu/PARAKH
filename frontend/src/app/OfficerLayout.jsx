import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useI18n } from '../lib/i18n'
import { guessIdentifierType } from '../lib/identifiers'
import { identifierMeta } from '../design/vocab'
import { ButtonLink, Icon } from '../design/ui'
import { Brand } from './Brand'
import { useAuth } from './AuthContext'

// Officer shell from the Stitch officer screens: left sidebar + top bar with an
// identifier-aware search. No "ISO certified" / "live CCTNS integration" footer
// (H.1). Sidebar items are filtered by role once Phase C adds roles.

const NAV = [
  ['/investigate', 'officer.nav.dashboard', 'dashboard', true],
  ['/investigate/cases', 'officer.nav.cases', 'folder_open', false],
  ['/investigate/queue', 'officer.nav.queue', 'inbox', false],
  ['/investigate/submit', 'officer.nav.submit', 'add_circle', false],
  ['/investigate/campaigns', 'officer.nav.campaigns', 'hub', false],
  ['/investigate/heatlist', 'officer.nav.heatlist', 'local_fire_department', false],
]

function SearchBox() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [value, setValue] = useState('')
  const type = guessIdentifierType(value)
  const meta = type ? identifierMeta(type) : null

  function submit(event) {
    event.preventDefault()
    const query = value.trim()
    if (!query) return
    navigate(`/investigate/cases?q=${encodeURIComponent(query)}`)
  }

  return (
    <form role="search" onSubmit={submit} className="relative min-w-0 flex-1">
      <label htmlFor="officer-search" className="sr-only">
        {t('officer.search_label')}
      </label>
      <Icon name="search" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" />
      <input
        id="officer-search"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder={t('officer.search')}
        className={`h-10 w-full rounded-chip border-[1.5px] border-line bg-card pl-10 pr-28 text-body-sm outline-none focus:border-primary ${
          meta ? 'font-mono' : ''
        }`}
      />
      {meta && (
        <span
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md px-2 py-0.5 text-label-ui uppercase"
          style={{ background: `color-mix(in srgb, ${meta.color} 12%, white)`, color: `color-mix(in srgb, ${meta.color} 70%, #0f172a)` }}
        >
          {meta.label} detected
        </span>
      )}
    </form>
  )
}

export function OfficerLayout() {
  const { t } = useI18n()
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  async function handleSignOut() {
    await signOut()
    navigate('/investigate/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen bg-canvas">
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-line bg-card px-3 py-4 transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${
          menuOpen ? 'translate-x-0 shadow-l3' : '-translate-x-full'
        }`}
      >
        <div className="px-2">
          <Brand to="/investigate" subtitle={t('brand.officer_sub')} />
        </div>
        <p className="mt-6 px-3 text-label-ui uppercase text-ink-3">Operational modules</p>
        <nav aria-label="Investigation" className="mt-2 flex flex-col gap-1">
          {NAV.map(([to, key, icon, end]) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-chip px-3 py-2.5 text-body-sm font-semibold ${
                  isActive ? 'bg-primary text-white shadow-l1' : 'text-ink-2 hover:bg-canvas hover:text-primary'
                }`
              }
            >
              <Icon name={icon} size={20} />
              {t(key)}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto rounded-card border border-line bg-canvas p-3">
          <p className="truncate text-body-sm font-semibold text-ink">{user?.username || '—'}</p>
          <p className="text-label-ui uppercase text-ink-3">{user?.role || ''}</p>
          <button
            type="button"
            onClick={handleSignOut}
            className="mt-3 inline-flex items-center gap-1.5 text-body-sm font-semibold text-ink-2 hover:text-risk-high-ink"
          >
            <Icon name="logout" size={18} />
            {t('officer.sign_out')}
          </button>
        </div>
      </aside>
      {menuOpen && <button type="button" aria-label="Close menu" className="fixed inset-0 z-30 bg-slate-900/20 lg:hidden" onClick={() => setMenuOpen(false)} />}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="glass sticky top-0 z-20 flex items-center gap-3 border-x-0 border-t-0 px-4 py-3 lg:px-8">
          <button
            type="button"
            className="grid h-10 w-10 place-items-center rounded-chip border border-line bg-card lg:hidden"
            aria-label="Open menu"
            onClick={() => setMenuOpen(true)}
          >
            <Icon name="menu" />
          </button>
          <SearchBox />
          <ButtonLink to="/investigate/submit" icon="add" size="sm" className="hidden sm:inline-flex">
            {t('officer.new_analysis')}
          </ButtonLink>
        </header>
        <main id="main" className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-6 lg:px-8">
          <Outlet />
        </main>
        <footer className="border-t border-line px-4 py-4 text-body-sm text-ink-3 lg:px-8">{t('officer.footer')}</footer>
      </div>
    </div>
  )
}
