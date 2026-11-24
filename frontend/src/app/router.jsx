import { lazy, Suspense } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { LoadingBlock } from '../design/ui'
import { CitizenLayout } from './CitizenLayout'
import { RequireOfficer } from './AuthContext'
import { NotFound, WorkInProgress } from './pages'

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
const StatesGallery = import.meta.env.DEV ? lazy(() => import('../dev/StatesGallery')) : null

const wip = (title, phase, source) => <WorkInProgress title={title} phase={phase} source={source} />

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

// Route table mirrors planversionalpha.md H.2–H.5. Each placeholder names the
// Stitch source it will be built from, so nothing looks finished when it isn't.
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
  { path: '/investigate/login', element: wip('Officer login', 'H.4', 'parakh_officer_login_law_enforcement_authentication') },
  {
    element: (
      <Lazy>
        <RequireOfficer>
          <OfficerLayout />
        </RequireOfficer>
      </Lazy>
    ),
    children: [
      { path: '/investigate', element: wip('Command dashboard', 'H.4', 'parakh_officer_dashboard_command_centre_1') },
      { path: '/investigate/cases', element: wip('Cases', 'H.4', 'parakh_case_table_empty_loading_error_states') },
      { path: '/investigate/submit', element: wip('New analysis', 'H.4', 'parakh_new_forensic_analysis_evidence_ingestion') },
      { path: '/investigate/case/:caseId', element: wip('Case dossier', 'H.4', 'parakh_case_detail_forensic_dossier_prk_20261118_k7p2qx') },
      { path: '/investigate/campaigns', element: wip('Campaign map', 'H.4', 'parakh_campaign_intelligence_syndicate_network_graph') },
      { path: '/investigate/heatlist', element: wip('Heat-list', 'H.4', 'parakh_heat_list_hot_identifiers_registry') },
      { path: '/investigate/identifier/:type/:value', element: wip('Identifier pivot', 'H.5', 'to be generated in Stitch') },
    ],
  },
]

export function createRouter() {
  return createBrowserRouter(routes)
}
