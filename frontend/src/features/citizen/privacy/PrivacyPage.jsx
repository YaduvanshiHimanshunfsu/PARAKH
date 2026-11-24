import { useQuery } from '@tanstack/react-query'
import { Card, Icon } from '../../../design/ui'
import { citizenApi } from '../../../lib/api'

// Plain-language privacy page (H.3). Every statement maps to code:
//   checks are not stored ................ ADR-001, app/api/routes.py
//   reports need consent ................. CitizenReportRequest.consent
//   results in memory only ............... src/app/ResultContext.jsx
//   evidence locker on device ............ src/lib/vault.js
//   AI provider / reputation providers ... app/config.py (only when keys are set)
//   rate limiting by IP .................. app/core/rate_limiter.py
// The AI line is read live from /parakh/meta so it matches this server.

function Row({ icon, title, hindi, children }) {
  return (
    <li className="flex gap-4">
      <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-primary-tint text-primary"><Icon name={icon} /></span>
      <div className="min-w-0">
        <h2 className="text-title-md text-ink">{title}</h2>
        {hindi && <p className="hi text-body-sm text-ink-3" lang="hi">{hindi}</p>}
        <div className="mt-1 text-body-md text-ink-2">{children}</div>
      </div>
    </li>
  )
}

export function PrivacyPage() {
  const meta = useQuery({ queryKey: ['meta'], queryFn: citizenApi.meta, staleTime: 600_000 })
  const ai = meta.data?.ai_configured
  return (
    <div className="mx-auto max-w-3xl px-4 py-8 md:px-8">
      <h1 className="text-headline-lg-mobile md:text-headline-lg">
        How PARAKH handles your data <span className="hi block text-accent-strong md:inline" lang="hi">/ आपकी जानकारी</span>
      </h1>
      <p className="mt-2 text-body-md text-ink-2">No login, no name, no phone number. This page lists exactly what happens to what you check.</p>

      <Card className="mt-6 p-5 md:p-6">
        <ul className="space-y-6">
          <Row icon="shield_lock" title="Checks are not stored" hindi="जाँच सहेजी नहीं जाती">
            Messages, links, emails, QR text and UPI IDs you check are analysed and then discarded by the server. The result stays in this browser tab only and disappears when you refresh or close it.
          </Row>
          <Row icon="local_police" title="Reports are stored only if you agree" hindi="रिपोर्ट केवल आपकी सहमति से">
            “Send to police” stores the item you checked and your optional note so officers can review it. It needs you to tick a consent box first. Your reference number shows only the report’s stage, never its content.
          </Row>
          <Row icon="lock" title="Evidence locker stays on your device" hindi="सबूत आपके डिवाइस पर">
            Items you save are encrypted in this browser. They are never uploaded. Clearing your browser data deletes them.
          </Row>
          <Row icon="memory" title="AI service" hindi="एआई सेवा">
            {meta.isPending && 'Checking this server’s setting…'}
            {meta.isError && 'Could not read this server’s setting.'}
            {meta.data &&
              (ai
                ? 'This server has the AI service (Google Gemini) switched on. Text you check, and text read from screenshots or voice notes, is sent to it for analysis. If it is unavailable, PARAKH’s offline rules are used.'
                : 'This server has the AI service switched off. Everything is checked with PARAKH’s offline rules, and screenshot or voice-note reading is unavailable.')}
          </Row>
          <Row icon="travel_explore" title="Link checks" hindi="लिंक जाँच">
            PARAKH reads the link address itself and may connect to the website only to read its security certificate — the page is not opened. If this server is set up with a link-reputation service, the address is also looked up there.
          </Row>
          <Row icon="android" title="App files" hindi="ऐप फ़ाइलें">
            An .apk you upload is read in memory to list its permissions and signer. It is never installed or run, and it is not saved.
          </Row>
          <Row icon="speed" title="Abuse protection" hindi="दुरुपयोग से सुरक्षा">
            To stop automated abuse, the server counts requests per network address for a short time. These counts are not linked to what you checked.
          </Row>
        </ul>
      </Card>

      <p className="mt-6 text-body-sm text-ink-3">
        PARAKH gives risk guidance, not legal proof. For money lost to fraud, call 1930 or report at cybercrime.gov.in.
      </p>
    </div>
  )
}

export default PrivacyPage
