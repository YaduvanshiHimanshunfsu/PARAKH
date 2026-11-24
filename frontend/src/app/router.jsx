import { lazy, Suspense } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { LoadingBlock } from '../design/ui'
import { CitizenLayout } from './CitizenLayout'
import { RequireOfficer } from './AuthContext'
import { NotFound, WorkInProgress } from './pages'

// The officer console is a separate chunk: citizens never download it.
const OfficerLayout = lazy(() => import('./OfficerLayout').then((m) => ({ default: m.OfficerLayout })))
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
      { path: '/', element: wip('Home', 'H.2', 'parakh_citizen_cyber_safety_portal') },
      { path: '/check', element: wip('Check something suspicious', 'H.2', 'parakh_check_something_suspicious_forensic_multi_modal_triage') },
      { path: '/result', element: wip('Verdict', 'H.2', 'parakh_verification_result_high_risk_scam_alert') },
      { path: '/apk', element: wip('App check', 'H.2', 'parakh_app_check_apk_forensic_scanner') },
      { path: '/rescue', element: wip('Emergency rescue', 'H.3', 'parakh_cyber_victim_rescue_emergency_sop') },
      { path: '/help', element: wip('Official help directory', 'H.3', 'parakh_official_help_directory_organisation_verifier') },
      { path: '/learn', element: wip('Scam explorer', 'H.3', 'parakh_scam_explorer_cyber_defence_academy') },
      { path: '/evidence', element: wip('Evidence locker', 'H.5', 'to be generated in Stitch') },
      { path: '/status/:reference', element: wip('Report status', 'H.5', 'to be generated in Stitch') },
      { path: '/privacy', element: wip('Privacy', 'H.3', 'plain page') },
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
