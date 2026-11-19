import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Flame, FolderSearch, LogOut, PlusCircle, ShieldAlert } from 'lucide-react'
import { useOfficerAuth } from './OfficerAuthContext'

const links = [
  ['/investigate', 'Cases', FolderSearch, true],
  ['/investigate/submit', 'New analysis', PlusCircle, false],
  ['/investigate/heatlist', 'Heat-list', Flame, false],
]

export function InvestigateLayout() {
  const { user, signOut } = useOfficerAuth()
  const navigate = useNavigate()

  async function handleSignOut() {
    await signOut()
    navigate('/investigate/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-900 text-white shadow-md">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 lg:px-6">
          <NavLink to="/investigate" className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-blue-600">
              <ShieldAlert size={19} />
            </span>
            <span>
              <span className="block text-sm font-bold leading-tight">PARAKH Investigate</span>
              <span className="block text-[11px] text-slate-400">Officer console</span>
            </span>
          </NavLink>

          <nav aria-label="Investigation navigation" className="flex items-center gap-1 text-[13px] font-semibold">
            {links.map(([to, label, Icon, end]) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded-lg px-3 py-2 transition ${
                    isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`
                }
              >
                <Icon size={15} />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3 text-xs">
            {user && (
              <span className="hidden text-slate-300 sm:inline">
                {user.username} · <span className="text-slate-400">{user.role}</span>
              </span>
            )}
            <button
              type="button"
              onClick={handleSignOut}
              className="flex items-center gap-1.5 rounded-lg bg-slate-800 px-3 py-2 font-semibold text-slate-200 transition hover:bg-slate-700"
            >
              <LogOut size={14} /> Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-6">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 py-5 text-center text-xs text-slate-500">
        Static automated analysis. Indicators support an investigation; they are not proof of
        criminal conduct.
      </footer>
    </div>
  )
}
