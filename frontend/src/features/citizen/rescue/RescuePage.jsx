import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ButtonLink, Card, CardHeader, ErrorBlock, Icon, LoadingBlock } from '../../../design/ui'
import { citizenApi } from '../../../lib/api'
import { EXPOSURE, SCAM_CATEGORY, hindiLabel, label } from '../../../content/labels'

// Built from design/stitch/parakh_cyber_victim_rescue_emergency_sop. The plan
// itself comes from POST /parakh/rescue-plan (app/services/rescue_planner.py);
// this screen only lets the person say what happened and ticks off steps.
// Ticks live in memory only. Unverifiable Stitch blocks (nearest station
// finder, counselling and legal-aid partners) are left out per H.1.

const EXPOSURE_ICON = {
  RECEIVED_ONLY: 'mark_email_unread',
  CLICKED_LINK: 'ads_click',
  SHARED_PERSONAL_INFO: 'badge',
  SHARED_SECRET: 'password',
  INSTALLED_APP_OR_SCREEN_SHARE: 'mobile_arrow_down',
  SENT_MONEY: 'currency_rupee',
}

const URGENCY = {
  CRITICAL: {
    tone: 'bg-risk-high-ink text-white',
    title: 'Act now — the first hours matter most',
    hindi: 'तुरंत कार्रवाई करें — शुरुआती घंटे सबसे ज़रूरी हैं',
    body: 'Reporting quickly to 1930 and your bank gives the best chance of stopping the money from moving further.',
  },
  HIGH: {
    tone: 'bg-risk-medium-bg text-risk-medium-ink border border-risk-medium/40',
    title: 'Secure your accounts today',
    hindi: 'आज ही अपने खाते सुरक्षित करें',
    body: 'Something sensitive may have been exposed. Follow the steps in order.',
  },
  PREVENTIVE: {
    tone: 'bg-risk-low-bg text-risk-low-ink border border-risk-low/40',
    title: 'You are safe if you stop here',
    hindi: 'यहीं रुकें तो आप सुरक्षित हैं',
    body: 'Nothing has been shared yet. These steps keep it that way.',
  },
}

const VERDICTS = ['SCAM', 'SUSPICIOUS', 'SAFE']

export function RescuePage() {
  const [params, setParams] = useSearchParams()
  const exposure = EXPOSURE[params.get('exposure')] ? params.get('exposure') : null
  const verdict = VERDICTS.includes(params.get('verdict')) ? params.get('verdict') : 'SCAM'
  const category = SCAM_CATEGORY[params.get('category')] ? params.get('category') : 'UNKNOWN'
  const [done, setDone] = useState({})

  const plan = useQuery({
    queryKey: ['rescue-plan', exposure, verdict, category],
    queryFn: () => citizenApi.rescuePlan({ exposure_state: exposure, verdict, scam_category: category }),
    enabled: Boolean(exposure),
  })

  function choose(key) {
    const next = new URLSearchParams(params)
    next.set('exposure', key)
    setParams(next, { replace: true })
    setDone({})
  }

  const urgency = plan.data ? URGENCY[plan.data.urgency] || URGENCY.HIGH : null
  const actions = plan.data ? [...plan.data.actions].sort((a, b) => a.priority - b.priority) : []
  const completed = actions.filter((_, index) => done[index]).length

  return (
    <div className="mx-auto max-w-[1180px] px-4 py-8 md:px-8">
      <p className="text-label-ui uppercase text-risk-high-ink">Emergency help</p>
      <h1 className="text-headline-lg-mobile md:text-headline-lg">
        Cyber fraud rescue plan <span className="hi block text-accent-strong md:inline" lang="hi">/ साइबर ठगी — तुरंत सहायता</span>
      </h1>
      <div className="mt-4 flex flex-wrap gap-2">
        <a href="tel:1930" className="inline-flex h-12 items-center gap-2 rounded-chip bg-risk-high-ink px-5 font-semibold text-white shadow-l2">
          <Icon name="call" filled /> Call 1930 now
        </a>
        <a href="https://cybercrime.gov.in/" target="_blank" rel="noreferrer" className="inline-flex h-12 items-center gap-2 rounded-chip border border-line bg-card px-5 font-semibold text-ink hover:text-primary">
          <Icon name="open_in_new" /> cybercrime.gov.in
        </a>
        <a href="tel:112" className="inline-flex h-12 items-center gap-2 rounded-chip border border-line bg-card px-5 font-semibold text-ink hover:text-primary">
          <Icon name="local_police" /> In danger? 112
        </a>
      </div>

      <section className="mt-8" aria-labelledby="what-happened">
        <h2 id="what-happened" className="text-headline-sm">
          What happened? <span className="hi text-body-md font-normal text-ink-2" lang="hi">क्या हुआ? अपनी स्थिति चुनें</span>
        </h2>
        <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3">
          {Object.keys(EXPOSURE).map((key) => {
            const active = key === exposure
            return (
              <button
                key={key}
                type="button"
                aria-pressed={active}
                onClick={() => choose(key)}
                className={`flex min-h-[96px] flex-col items-start gap-2 rounded-card border-2 p-4 text-left transition-colors ${
                  active ? 'border-primary bg-primary-tint' : 'border-line bg-card hover:border-primary/50'
                }`}
              >
                <Icon name={EXPOSURE_ICON[key]} className={active ? 'text-primary' : 'text-ink-2'} />
                <span className="text-body-md font-semibold text-ink">{label(EXPOSURE, key)}</span>
                <span className="hi text-body-sm text-ink-2" lang="hi">{hindiLabel(EXPOSURE, key)}</span>
              </button>
            )
          })}
        </div>
      </section>

      {!exposure && (
        <p className="mt-6 rounded-card border border-dashed border-line p-5 text-center text-body-md text-ink-2">
          Choose what happened to see your step-by-step plan.
        </p>
      )}

      {exposure && plan.isPending && <div className="mt-6"><LoadingBlock rows={4} /></div>}
      {exposure && plan.isError && <Card className="mt-6"><ErrorBlock error={plan.error} onRetry={() => plan.refetch()} /></Card>}

      {plan.data && (
        <div className="mt-6 space-y-6">
          <div className={`rounded-hero p-5 md:p-6 ${urgency.tone}`} role="status">
            <p className="text-headline-sm">{urgency.title}</p>
            <p className="hi text-body-md opacity-90" lang="hi">{urgency.hindi}</p>
            <p className="mt-2 text-body-md opacity-90">{urgency.body}</p>
          </div>

          <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
            <Card className="p-5 md:p-6">
              <CardHeader
                title={plan.data.title}
                hindi="क्रमबद्ध सुरक्षा प्रक्रिया"
                action={<span className="rounded-chip bg-canvas px-3 py-1 text-body-sm font-semibold text-ink-2 tnum">{completed} / {actions.length} done</span>}
              />
              <ol className="mt-4 space-y-3">
                {actions.map((action, index) => (
                  <li key={action.instruction} className={`flex gap-3 rounded-chip border p-3 ${done[index] ? 'border-risk-low/40 bg-risk-low-bg' : 'border-line'}`}>
                    <input
                      type="checkbox"
                      checked={Boolean(done[index])}
                      onChange={(event) => setDone({ ...done, [index]: event.target.checked })}
                      aria-label={`Mark step ${index + 1} done`}
                      className="mt-1 h-5 w-5 shrink-0 accent-[#15803d]"
                    />
                    <div className="min-w-0">
                      <p className="text-label-ui uppercase text-ink-3">Step {index + 1}</p>
                      <p className={`text-body-md ${done[index] ? 'text-ink-2 line-through' : 'text-ink'}`}>{action.instruction}</p>
                      {action.official_url && (
                        <a href={action.official_url} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 break-all text-body-sm font-semibold text-primary underline">
                          {action.official_url.replace(/^https?:\/\//, '').replace(/\/$/, '')} <Icon name="open_in_new" size={14} />
                        </a>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
              <p className="mt-3 text-body-sm text-ink-3">Ticks are kept only on this screen and are not sent anywhere.</p>
            </Card>

            <div className="space-y-4">
              {plan.data.evidence_to_preserve.length > 0 && (
                <Card className="p-5">
                  <CardHeader title="Keep this evidence" hindi="ये सबूत सँभालकर रखें" />
                  <ul className="mt-3 space-y-2">
                    {plan.data.evidence_to_preserve.map((item) => (
                      <li key={item} className="flex gap-2 text-body-sm text-ink">
                        <Icon name="inventory_2" size={18} className="mt-0.5 shrink-0 text-primary" /> {item}
                      </li>
                    ))}
                  </ul>
                  <ButtonLink to="/evidence" variant="ghost" size="sm" icon="lock" className="mt-4">Open my evidence locker</ButtonLink>
                </Card>
              )}
              <div className="rounded-card bg-sand p-5">
                <p className="hi text-title-md text-ink" lang="hi">धोखाधड़ी किसी के साथ भी हो सकती है — यह आपकी गलती नहीं है।</p>
                <p className="mt-1 text-body-sm text-ink-2">Fraud can happen to anyone. Reporting quickly helps you and protects the next person.</p>
              </div>
              <div className="rounded-card border border-line bg-surface-container-low p-4 text-body-sm text-ink-2">
                <p className="font-semibold text-ink">Limits of this plan</p>
                <ul className="mt-1 list-disc space-y-0.5 pl-5">
                  {plan.data.limitations.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default RescuePage
