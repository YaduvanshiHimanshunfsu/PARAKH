import { lazy, Suspense } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { LoadingBlock } from '../design/ui'
import { CitizenLayout } from './CitizenLayout'
import { RequireOfficer } from './AuthContext'
import { NotFound } from './pages'

// The officer console is a separate chunk: citizens never download it.
const OfficerLayout = lazy(() => import('./OfficerLayout').then((m) => ({ default: m.OfficerLayout })))
const page = (loader, name) => lazy(() => loader().then((m) => ({ default: m[name] })))
const HomePage = page(() => import('../features/citizen/home/HomePage'), 'HomePage')
const CheckPage = page(() => import('../features/citizen/check/CheckPage'), 'CheckPage')
const ResultPage = page(() => import('../features/citizen/result/ResultPage'), 'ResultPage')
const ApkPage = page(() => import('../features/citizen/apk/ApkPage'), 'ApkPage')
const RescuePage = page(() => import('../features/citizen/rescue/RescuePage'), 'RescuePage')
const HelpPage = page(() => import('../features/citizen/help/HelpPage'), 'HelpPage')
const LearnPage = page(() => import('../features/citizen/learn/LearnPage'), 'LearnPage')
const EvidencePage = page(() => import('../features/citizen/evidence/EvidencePage'), 'EvidencePage')
const StatusPage = page(() => import('../features/citizen/status/StatusPage'), 'StatusPage')
const PrivacyPage = page(() => import('../features/citizen/privacy/PrivacyPage'), 'PrivacyPage')
const LoginPage = page(() => import('../features/officer/LoginPage'), 'LoginPage')
const DashboardPage = page(() => import('../features/officer/DashboardPage'), 'DashboardPage')
const CasesPage = page(() => import('../features/officer/CasesPage'), 'CasesPage')
const SubmitPage = page(() => import('../features/officer/SubmitPage'), 'SubmitPage')
const CaseDetailPage = page(() => import('../features/officer/CaseDetailPage'), 'CaseDetailPage')
const CampaignsPage = page(() => import('../features/officer/campaigns/CampaignsPage'), 'CampaignsPage')
const HeatlistPage = page(() => import('../features/officer/HeatlistPage'), 'HeatlistPage')
const IdentifierPage = page(() => import('../features/officer/IdentifierPage'), 'IdentifierPage')
const StatesGallery = import.meta.env.DEV ? lazy(() => import('../dev/StatesGallery')) : null

function Lazy({ children }) {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-3xl p-10">
          <LoadingBlock rows={4} />
        </div>
      }
    >
      {children}
    </Suspense>
  )
}

// Route table mirrors planversionalpha.md H.2–H.5. Every page is lazy-loaded;
// the officer console is a separate chunk citizens never download.
export const routes = [
  {
    element: <CitizenLayout />,
    children: [
      { path: '/', element: <Lazy><HomePage /></Lazy> },
      { path: '/check', element: <Lazy><CheckPage /></Lazy> },
      { path: '/result', element: <Lazy><ResultPage /></Lazy> },
      { path: '/apk', element: <Lazy><ApkPage /></Lazy> },
      { path: '/rescue', element: <Lazy><RescuePage /></Lazy> },
      { path: '/help', element: <Lazy><HelpPage /></Lazy> },
      { path: '/learn', element: <Lazy><LearnPage /></Lazy> },
      { path: '/evidence', element: <Lazy><EvidencePage /></Lazy> },
      { path: '/status', element: <Lazy><StatusPage /></Lazy> },
      { path: '/status/:reference', element: <Lazy><StatusPage /></Lazy> },
      { path: '/privacy', element: <Lazy><PrivacyPage /></Lazy> },
      ...(StatesGallery ? [{ path: '/__states', element: <Lazy><StatesGallery /></Lazy> }] : []),
      { path: '*', element: <NotFound /> },
    ],
  },
  { path: '/investigate/login', element: <Lazy><LoginPage /></Lazy> },
  {
    element: (
      <Lazy>
        <RequireOfficer>
          <OfficerLayout />
        </RequireOfficer>
      </Lazy>
    ),
    children: [
      { path: '/investigate', element: <Lazy><DashboardPage /></Lazy> },
      { path: '/investigate/cases', element: <Lazy><CasesPage /></Lazy> },
      { path: '/investigate/submit', element: <Lazy><SubmitPage /></Lazy> },
      { path: '/investigate/case/:caseId', element: <Lazy><CaseDetailPage /></Lazy> },
      { path: '/investigate/campaigns', element: <Lazy><CampaignsPage /></Lazy> },
      { path: '/investigate/heatlist', element: <Lazy><HeatlistPage /></Lazy> },
      { path: '/investigate/identifier/:type/:value', element: <Lazy><IdentifierPage /></Lazy> },
    ],
  },
]

export function createRouter() {
  return createBrowserRouter(routes)
}
