import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Button, Card, Icon, RiskBadge, Segmented } from '../../../design/ui'
import { toRiskLevel } from '../../../design/vocab'
import { citizenApi } from '../../../lib/api'
import { SCAM_CATEGORY, label } from '../../../content/labels'
import scams from '../../../content/scams.json'

// Built from design/stitch/parakh_scam_explorer_cyber_defence_academy.
// Scam types come from src/content/scams.json. The quiz lets the reader ask
// the real analyser about each example, so the lesson and the product agree.
// Stitch "downloadable posters" are left out: no such files exist.

const GROUPS = [
  { value: 'all', label: 'All', hindi: 'सभी' },
  { value: 'financial', label: 'Money & banking', hindi: 'पैसा' },
  { value: 'identity', label: 'Fake officials & apps', hindi: 'नकली अधिकारी' },
  { value: 'jobs', label: 'Jobs & investment', hindi: 'नौकरी / निवेश' },
  { value: 'social', label: 'Social & blackmail', hindi: 'सोशल' },
]

// Genuine-pattern messages for the quiz, written for this page. They are
// deliberately ordinary: an OTP that warns not to share it, a debit alert
// pointing to the bank's own number, a delivery update with no link or fee.
const GENUINE = [
  {
    id: 'genuine_otp',
    text: '482913 is your OTP for login to your bank account. Valid for 5 minutes. Do not share this OTP with anyone, including bank staff.',
    why: 'It tells you not to share the OTP and asks you to do nothing. An OTP you did not request is still a warning sign — someone may be trying your account.',
  },
  {
    id: 'genuine_debit',
    text: 'Rs 1,250.00 debited from A/c XX4521 on 21-11 by UPI. If not done by you, call the number on the back of your debit card.',
    why: 'It sends you to a number you already have (your card), not a number or link in the message.',
  },
  {
    id: 'genuine_delivery',
    text: 'Your order will be delivered today between 2 PM and 6 PM. Track it in the app you ordered from.',
    why: 'No link, no fee, no deadline. It points you to the app you already use.',
  },
]

function shuffleStable(items) {
  // Deterministic interleave so the quiz order is the same for everyone.
  const out = []
  const scamItems = items.filter((item) => item.scam)
  const safeItems = items.filter((item) => !item.scam)
  while (scamItems.length || safeItems.length) {
    if (scamItems.length) out.push(scamItems.shift())
    if (scamItems.length) out.push(scamItems.shift())
    if (safeItems.length) out.push(safeItems.shift())
  }
  return out
}

function ScamCard({ scam, hindi }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  return (
    <Card className="flex flex-col p-5">
      <div className="flex items-start justify-between gap-2">
        <span className="grid h-11 w-11 place-items-center rounded-xl bg-accent-tint text-accent-strong">
          <Icon name={scam.icon} />
        </span>
        <span className="rounded-chip bg-canvas px-2 py-0.5 text-label-ui uppercase text-ink-2">{scam.tag}</span>
      </div>
      <h3 className="mt-3 text-title-md text-ink">{hindi ? scam.hindi : scam.title}</h3>
      <p className={`text-body-sm text-ink-3 ${hindi ? '' : 'hi'}`} lang={hindi ? 'en' : 'hi'}>{hindi ? scam.title : scam.hindi}</p>
      <blockquote className="mt-3 rounded-chip border-l-4 border-risk-high bg-risk-high-bg/60 p-3 text-body-sm italic text-ink">“{scam.example}”</blockquote>
      {open && (
        <div className="mt-3 space-y-2 text-body-sm">
          <p className="flex gap-2 text-ink">
            <Icon name="flag" size={18} className="shrink-0 text-risk-high-ink" />
            <span className={hindi ? 'hi' : ''} lang={hindi ? 'hi' : undefined}>{hindi ? scam.red_flag_hi : scam.red_flag}</span>
          </p>
          <p className="flex gap-2 text-ink">
            <Icon name="health_and_safety" size={18} className="shrink-0 text-risk-low" />
            <span className={hindi ? 'hi' : ''} lang={hindi ? 'hi' : undefined}>{hindi ? scam.safety_hi : scam.safety}</span>
          </p>
        </div>
      )}
      <div className="mt-auto flex flex-wrap gap-2 pt-4">
        <Button variant="ghost" size="sm" icon={open ? 'expand_less' : 'expand_more'} onClick={() => setOpen(!open)} aria-expanded={open}>
          {open ? 'Hide' : 'Red flags & safety'}
        </Button>
        <Button variant="subtle" size="sm" icon="search_check" onClick={() => navigate('/check?mode=message', { state: { text: scam.example } })}>
          Check this example
        </Button>
      </div>
    </Card>
  )
}

function Quiz() {
  const items = useMemo(
    () =>
      shuffleStable([
        ...scams.types.slice(0, 6).map((scam) => ({ id: scam.id, text: scam.example, scam: true, why: scam.red_flag })),
        ...GENUINE.map((item) => ({ ...item, scam: false })),
      ]),
    [],
  )
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const ask = useMutation({ mutationFn: (text) => citizenApi.analyseMessage(text, 'auto') })
  const item = items[index]
  const answer = answers[item.id]
  const score = items.filter((entry) => answers[entry.id] !== undefined && answers[entry.id] === entry.scam).length
  const answered = Object.keys(answers).length

  function next(step) {
    ask.reset()
    setIndex((index + step + items.length) % items.length)
  }

  return (
    <Card className="p-5 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-headline-sm">
          Would you trust this? <span className="hi text-body-md font-normal text-ink-2" lang="hi">क्या आप भरोसा करेंगे?</span>
        </h2>
        <p className="text-body-sm text-ink-2 tnum" aria-live="polite">
          Score {score} / {answered} · Question {index + 1} of {items.length}
        </p>
      </div>
      <p className="mt-4 rounded-card bg-canvas p-4 text-body-lg text-ink">{item.text}</p>
      {answer === undefined ? (
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="danger" icon="gpp_maybe" onClick={() => setAnswers({ ...answers, [item.id]: true })}>Scam</Button>
          <Button variant="ghost" icon="verified_user" onClick={() => setAnswers({ ...answers, [item.id]: false })}>Looks genuine</Button>
        </div>
      ) : (
        <div className="mt-4 rounded-card border border-line p-4" role="status">
          <p className={`text-title-md ${answer === item.scam ? 'text-risk-low-ink' : 'text-risk-high-ink'}`}>
            {answer === item.scam ? 'Correct.' : 'Not quite.'} {item.scam ? 'This is a scam.' : 'This follows the pattern of a genuine message.'}
          </p>
          <p className="mt-1 text-body-md text-ink-2">{item.why}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button variant="subtle" size="sm" icon="shield" loading={ask.isPending} onClick={() => ask.mutate(item.text)}>
              Ask PARAKH’s analyser
            </Button>
            {ask.data && (
              <span className="inline-flex flex-wrap items-center gap-2 text-body-sm text-ink-2">
                <RiskBadge level={toRiskLevel(ask.data.verdict)} score={ask.data.confidence} />
                {ask.data.scam_category !== 'UNKNOWN' && label(SCAM_CATEGORY, ask.data.scam_category)}
              </span>
            )}
            {ask.isError && <span role="alert" className="text-body-sm text-risk-high-ink">{ask.error.message}</span>}
          </div>
        </div>
      )}
      <div className="mt-5 flex justify-between">
        <Button variant="ghost" size="sm" icon="arrow_back" onClick={() => next(-1)}>Previous</Button>
        <Button variant="ghost" size="sm" iconRight="arrow_forward" onClick={() => next(1)}>Next</Button>
      </div>
    </Card>
  )
}

export function LearnPage() {
  const [group, setGroup] = useState('all')
  const [hindi, setHindi] = useState(false)
  const visible = scams.types.filter((scam) => group === 'all' || scam.group === group)
  return (
    <div className="mx-auto max-w-[1280px] px-4 py-8 md:px-8">
      <h1 className="text-headline-lg-mobile md:text-headline-lg">
        Know the scams <span className="hi block text-accent-strong md:inline" lang="hi">/ ठगी के तरीके पहचानें</span>
      </h1>
      <p className="mt-1 max-w-3xl text-body-md text-ink-2">
        {scams.types.length} scam types reported across India, with the warning sign to look for and the safe thing to do. Examples are rewritten from public police and CERT-In advisories.
      </p>

      <ol className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ['notifications', 'You receive something odd', 'कुछ अजीब मिला'],
          ['content_paste', 'Paste or upload it in PARAKH', 'परख में चिपकाएँ'],
          ['rule', 'Read the reasons, not just the colour', 'कारण पढ़ें'],
          ['health_and_safety', 'Follow the safe next step', 'सुरक्षित कदम उठाएँ'],
        ].map(([icon, text, hi], index) => (
          <li key={text} className="flex items-center gap-3 rounded-card border border-line bg-card p-4">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-primary text-white"><Icon name={icon} size={20} /></span>
            <span className="text-body-sm font-semibold text-ink">
              {index + 1}. {text}
              <span className="hi block font-normal text-ink-3" lang="hi">{hi}</span>
            </span>
          </li>
        ))}
      </ol>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <Segmented label="Scam group" value={group} onChange={setGroup} options={GROUPS} size="sm" />
        <Segmented
          label="Card language"
          size="sm"
          value={hindi ? 'hi' : 'en'}
          onChange={(value) => setHindi(value === 'hi')}
          options={[
            { value: 'en', label: 'English' },
            { value: 'hi', label: 'हिंदी' },
          ]}
        />
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {visible.map((scam) => (
          <ScamCard key={scam.id} scam={scam} hindi={hindi} />
        ))}
      </div>

      <div className="mt-10">
        <Quiz />
      </div>
    </div>
  )
}

export default LearnPage
