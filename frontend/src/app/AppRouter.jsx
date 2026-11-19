import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './AppLayout'
import { InvestigateLayout } from './InvestigateLayout'
import { OfficerAuthProvider, RequireOfficer } from './OfficerAuthContext'
import { HomePage } from '../pages/HomePage'
import { CheckPage } from '../pages/CheckPage'
import { ResultPage } from '../pages/ResultPage'
import { RescuePage } from '../pages/RescuePage'
import { EvidencePage } from '../pages/EvidencePage'
import { HelpPage } from '../pages/HelpPage'
import { LearnPage } from '../pages/LearnPage'
import { LoginPage } from '../pages/investigate/LoginPage'
import { CaseListPage } from '../pages/investigate/CaseListPage'
import { CaseDetailPage } from '../pages/investigate/CaseDetailPage'
import { IdentifierPage } from '../pages/investigate/IdentifierPage'
import { HeatListPage } from '../pages/investigate/HeatListPage'
import { SubmitPage } from '../pages/investigate/SubmitPage'

export function AppRouter() {
  return (
    <OfficerAuthProvider>
      <Routes>
        {/* Citizen Mode — anonymous, nothing persisted. */}
        <Route element={<AppLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/check" element={<CheckPage />} />
          <Route path="/result" element={<ResultPage />} />
          <Route path="/rescue" element={<RescuePage />} />
          <Route path="/evidence" element={<EvidencePage />} />
          <Route path="/help" element={<HelpPage />} />
          <Route path="/learn" element={<LearnPage />} />
        </Route>

        {/* Investigation Mode — officer only. */}
        <Route path="/investigate/login" element={<LoginPage />} />
        <Route
          element={
            <RequireOfficer>
              <InvestigateLayout />
            </RequireOfficer>
          }
        >
          <Route path="/investigate" element={<CaseListPage />} />
          <Route path="/investigate/submit" element={<SubmitPage />} />
          <Route path="/investigate/heatlist" element={<HeatListPage />} />
          <Route path="/investigate/case/:caseId" element={<CaseDetailPage />} />
          <Route path="/investigate/identifier/:type/:value" element={<IdentifierPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </OfficerAuthProvider>
  )
}
