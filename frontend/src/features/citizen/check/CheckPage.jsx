import { useEffect, useRef, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Button, ButtonLink, Card, ConsentCheckbox, FileDrop, Icon, IdentifierChip, Segmented, Stepper, useToast } from '../../../design/ui'
import { citizenApi } from '../../../lib/api'
import { detectIdentifiers } from '../../../lib/identifiers'
import { cameraAvailable, decodeQrFile, decodeQrFrame } from '../../../lib/qr'
import { useCheck } from '../useCheck'

// Built from design/stitch/parakh_check_something_suspicious_forensic_multi_modal_triage
// (desktop) and parakh_citizen_mobile_check / citizen_app_check_something_suspicious_mobile
// (mobile). The Stitch "Live sample / Empty / Validation error" preview toggles
// are replaced by real state. Every mode calls a real endpoint.

const MODES = [
  { value: 'message', label: 'Message', hindi: 'संदेश', icon: 'sms' },
  { value: 'link', label: 'Link', hindi: 'लिंक', icon: 'link' },
  { value: 'email', label: 'Email', hindi: 'ईमेल', icon: 'mail' },
  { value: 'screenshot', label: 'Screenshot', hindi: 'स्क्रीनशॉट', icon: 'image_search' },
  { value: 'voice', label: 'Voice note', hindi: 'वॉइस', icon: 'mic' },
  { value: 'qr', label: 'QR code', hindi: 'क्यूआर', icon: 'qr_code_scanner' },
  { value: 'identifier', label: 'UPI / Phone', hindi: 'यूपीआई / फोन', icon: 'account_balance_wallet' },
]

const LANGUAGES = [
  ['auto', 'Auto-detect'],
  ['en', 'English'],
  ['hi', 'हिंदी (Hindi)'],
  ['hinglish', 'Hinglish'],
]

// Clearly labelled practice samples (synthetic, from public advisory patterns).
const SAMPLES = {
  message:
    'Dear consumer, your electricity will be disconnected tonight at 9:30 PM due to pending bill. Update meter immediately, call 9988776655.',
  link: 'https://sbi-verify-kyc.in/urgent',
  identifier: 'richplan@ybl',
  qr: 'upi://pay?pa=richplan@ybl&pn=RichPlan&am=5000',
}

const inputClass =
  'w-full rounded-chip border-[1.5px] border-line bg-white p-3 text-body-md outline-none focus:border-primary'

function LiveChips({ text }) {
  const chips = detectIdentifiers(text).slice(0, 8)
  if (!chips.length) return null
  return (
    <div className="mt-3">
      <p className="text-label-ui uppercase text-ink-2">
        Found while you type <span className="hi normal-case text-ink-3" lang="hi">· लिखते समय मिले</span>
      </p>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {chips.map((chip) => (
          <IdentifierChip key={`${chip.type}:${chip.value}`} type={chip.type} value={chip.value} copy={false} />
        ))}
      </div>
    </div>
  )
}

function SampleButton({ onUse }) {
  return (
    <button type="button" onClick={onUse} className="inline-flex items-center gap-1 text-body-sm font-semibold text-primary hover:underline">
      <Icon name="science" size={16} /> Try a practice sample
    </button>
  )
}

function MessageMode({ check, initialText = '' }) {
  const [text, setText] = useState(initialText)
  const [language, setLanguage] = useState('auto')
  const tooShort = text.trim().length < 3
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (!tooShort) check.mutate({ kind: 'message', input: { text: text.trim(), language } })
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor="message-input" className="text-title-md">
          Paste the message <span className="hi text-body-sm font-normal text-ink-2" lang="hi">· संदेश चिपकाएँ</span>
        </label>
        <div className="flex items-center gap-3">
          <SampleButton onUse={() => setText(SAMPLES.message)} />
          <label className="flex items-center gap-1.5 text-body-sm text-ink-2">
            Language
            <select value={language} onChange={(event) => setLanguage(event.target.value)} className="h-9 rounded-chip border border-line bg-white px-2 text-body-sm">
              {LANGUAGES.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <textarea
        id="message-input"
        value={text}
        onChange={(event) => setText(event.target.value)}
        rows={7}
        maxLength={5000}
        placeholder="Paste the SMS, WhatsApp or chat message exactly as you received it… / संदेश वैसा ही चिपकाएँ जैसा मिला था…"
        className={`${inputClass} mt-2 resize-y`}
      />
      <div className="mt-1 flex justify-between text-body-sm text-ink-3">
        <span>Text you paste is checked, not saved.</span>
        <span className="tnum">{text.length} / 5000</span>
      </div>
      <LiveChips text={text} />
      <Button type="submit" size="lg" icon="shield" className="mt-4" loading={check.isPending} disabled={tooShort}>
        Analyse message <span className="hi font-normal" lang="hi">/ विश्लेषण करें</span>
      </Button>
    </form>
  )
}

function LinkMode({ check }) {
  const [url, setUrl] = useState('')
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (url.trim().length >= 4) check.mutate({ kind: 'url', input: { url: url.trim() } })
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor="link-input" className="text-title-md">
          Check a link before you open it <span className="hi text-body-sm font-normal text-ink-2" lang="hi">· खोलने से पहले जाँचें</span>
        </label>
        <SampleButton onUse={() => setUrl(SAMPLES.link)} />
      </div>
      <input id="link-input" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://…" inputMode="url" className={`${inputClass} mt-2 font-mono`} />
      <p className="mt-2 text-body-sm text-ink-2">
        PARAKH checks the address itself — look-alike names, risky endings, short links and HTTPS. The page is never opened.
      </p>
      <Button type="submit" size="lg" icon="travel_explore" className="mt-4" loading={check.isPending} disabled={url.trim().length < 4}>
        Check link
      </Button>
    </form>
  )
}

function EmailMode({ check }) {
  const [tab, setTab] = useState('paste')
  const [email, setEmail] = useState({ sender: '', subject: '', body: '', raw_eml: '' })
  const toast = useToast()
  const ready = tab === 'paste' ? email.body.trim().length >= 3 : email.raw_eml.trim().length > 0

  async function readFile(file) {
    if (file.size > 950_000) return toast('Use an .eml file smaller than 950 KB.', 'error')
    setEmail((current) => ({ ...current, raw_eml: '' }))
    const text = await file.text()
    setEmail((current) => ({ ...current, raw_eml: text }))
    toast(`${file.name} loaded`, 'success')
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (!ready) return
        const payload = tab === 'paste' ? { sender: email.sender || null, subject: email.subject || null, body: email.body } : { raw_eml: email.raw_eml }
        check.mutate({ kind: 'email', input: { email: { ...payload, language: 'auto' } } })
      }}
    >
      <Segmented
        label="Email input"
        size="sm"
        value={tab}
        onChange={setTab}
        options={[
          { value: 'paste', label: 'Paste email', icon: 'content_paste' },
          { value: 'eml', label: 'Upload .eml file', icon: 'upload_file' },
        ]}
      />
      {tab === 'paste' ? (
        <div className="mt-4 grid gap-3">
          <input value={email.sender} onChange={(event) => setEmail({ ...email, sender: event.target.value })} placeholder="From (sender address)" className={inputClass} aria-label="Sender" />
          <input value={email.subject} onChange={(event) => setEmail({ ...email, subject: event.target.value })} placeholder="Subject" className={inputClass} aria-label="Subject" />
          <textarea value={email.body} onChange={(event) => setEmail({ ...email, body: event.target.value })} rows={6} placeholder="Email text" className={`${inputClass} resize-y`} aria-label="Email body" />
        </div>
      ) : (
        <div className="mt-4">
          <FileDrop accept=".eml,message/rfc822" icon="mail" title={email.raw_eml ? '.eml file loaded' : 'Drop the .eml file'} hint="Attachments are never opened. Headers are checked for SPF, DKIM and DMARC." onFile={readFile} />
        </div>
      )}
      <Button type="submit" size="lg" icon="mark_email_read" className="mt-4" loading={check.isPending} disabled={!ready}>
        Analyse email
      </Button>
    </form>
  )
}

function MediaMode({ kind, check }) {
  const [consent, setConsent] = useState(false)
  const [file, setFile] = useState(null)
  const [text, setText] = useState('')
  const isVoice = kind === 'voice'
  const extract = useMutation({
    mutationFn: () => citizenApi.extractMedia(file, isVoice ? 'VOICE_NOTE' : 'SCREENSHOT', consent),
    onSuccess: (result) => setText(result.extracted_text),
  })

  return (
    <div>
      <h2 className="text-title-md">
        {isVoice ? 'Check a voice note' : 'Check a screenshot'}{' '}
        <span className="hi text-body-sm font-normal text-ink-2" lang="hi">· {isVoice ? 'वॉइस नोट' : 'स्क्रीनशॉट'}</span>
      </h2>
      <p className="mt-1 text-body-sm text-ink-2">
        The text is read from your file, shown to you for review, and then checked like a message. The file is not saved.
      </p>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <FileDrop
          accept={isVoice ? 'audio/mpeg,audio/wav,audio/webm,audio/mp4,audio/x-m4a' : 'image/png,image/jpeg,image/webp'}
          icon={isVoice ? 'mic' : 'image_search'}
          title={file ? file.name : isVoice ? 'Drop a voice note' : 'Drop a screenshot'}
          hint={isVoice ? 'MP3, WAV, WEBM or M4A · up to 3 MB' : 'PNG, JPG or WEBP · up to 3 MB'}
          onFile={(picked) => {
            setFile(picked)
            setText('')
            extract.reset()
          }}
        />
        <div className="space-y-3">
          <ConsentCheckbox checked={consent} onChange={setConsent} hindi="मैं सहमत हूँ कि फ़ाइल केवल पाठ पढ़ने के लिए उपयोग होगी और सहेजी नहीं जाएगी।">
            I agree this file is used only to read its text and is not stored.
          </ConsentCheckbox>
          <Button variant="ghost" icon="document_scanner" disabled={!file || !consent} loading={extract.isPending} onClick={() => extract.mutate()}>
            Read text from file
          </Button>
          {extract.isError && (
            <p role="alert" className="rounded-chip bg-risk-medium-bg p-3 text-body-sm text-risk-medium-ink">
              {extract.error.status === 503
                ? 'Reading files needs the AI service, which is switched off on this server. Please type or paste the text instead.'
                : extract.error.message}
            </p>
          )}
        </div>
      </div>
      <label htmlFor="media-text" className="mt-4 block text-title-md">
        Text to check <span className="text-body-sm font-normal text-ink-2">— review and correct before analysing</span>
      </label>
      <textarea id="media-text" value={text} onChange={(event) => setText(event.target.value)} rows={5} placeholder="The text read from your file appears here. You can also type it." className={`${inputClass} mt-2 resize-y`} />
      <LiveChips text={text} />
      <Button
        size="lg"
        icon="shield"
        className="mt-4"
        loading={check.isPending}
        disabled={text.trim().length < 3}
        onClick={() => check.mutate({ kind, input: { text: text.trim(), language: 'auto' } })}
      >
        Analyse text
      </Button>
    </div>
  )
}

function QrMode({ check }) {
  const [payload, setPayload] = useState('')
  const [camera, setCamera] = useState(false)
  const [error, setError] = useState('')
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const timerRef = useRef(null)

  function stopCamera() {
    if (timerRef.current) window.clearInterval(timerRef.current)
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    timerRef.current = null
    setCamera(false)
  }
  useEffect(() => stopCamera, [])

  function analyse(value) {
    const text = (value ?? payload).trim()
    if (text) check.mutate({ kind: 'qr', input: { payload: text } })
  }

  async function startCamera() {
    setError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
      streamRef.current = stream
      setCamera(true)
      requestAnimationFrame(async () => {
        if (!videoRef.current) return
        videoRef.current.srcObject = stream
        await videoRef.current.play()
        timerRef.current = window.setInterval(async () => {
          const value = await decodeQrFrame(videoRef.current)
          if (value) {
            stopCamera()
            setPayload(value)
            analyse(value)
          }
        }, 400)
      })
    } catch {
      setError('Camera access was not available. Upload a photo of the QR code instead.')
    }
  }

  return (
    <div>
      <h2 className="text-title-md">
        Check a QR code before you scan to pay <span className="hi text-body-sm font-normal text-ink-2" lang="hi">· भुगतान से पहले क्यूआर जाँचें</span>
      </h2>
      <p className="mt-1 text-body-sm text-ink-2">The QR is decoded on your device. Only its text is checked; the image is never uploaded.</p>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          {camera ? (
            <div className="relative overflow-hidden rounded-card bg-ink">
              <video ref={videoRef} muted playsInline className="aspect-square w-full object-cover" />
              <div className="pointer-events-none absolute inset-[18%] rounded-xl border-2 border-white/80" />
              <Button variant="ghost" size="sm" icon="stop" className="absolute bottom-3 left-3" onClick={stopCamera}>Stop</Button>
            </div>
          ) : (
            <FileDrop
              accept="image/png,image/jpeg,image/webp"
              icon="qr_code_2"
              title="Upload a photo of the QR code"
              hint="PNG, JPG or WEBP"
              onFile={async (file) => {
                setError('')
                try {
                  const value = await decodeQrFile(file)
                  setPayload(value)
                  analyse(value)
                } catch (caught) {
                  setError(caught.message)
                }
              }}
            />
          )}
          {!camera && cameraAvailable() && (
            <Button variant="ghost" icon="photo_camera" className="mt-3" onClick={startCamera}>Scan with camera</Button>
          )}
          {error && <p role="alert" className="mt-2 text-body-sm text-risk-high-ink">{error}</p>}
        </div>
        <div>
          <div className="flex items-center justify-between">
            <label htmlFor="qr-payload" className="text-title-md">Or paste the QR text</label>
            <SampleButton onUse={() => setPayload(SAMPLES.qr)} />
          </div>
          <textarea id="qr-payload" value={payload} onChange={(event) => setPayload(event.target.value)} rows={4} placeholder="upi://pay?pa=… or https://…" className={`${inputClass} mt-2 font-mono text-body-sm`} />
          <Button size="lg" icon="qr_code_scanner" className="mt-3" loading={check.isPending} disabled={!payload.trim()} onClick={() => analyse()}>
            Check QR
          </Button>
        </div>
      </div>
    </div>
  )
}

function IdentifierMode({ check }) {
  const [value, setValue] = useState('')
  const found = detectIdentifiers(value)[0]
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (value.trim().length >= 3) check.mutate({ kind: 'identifier', input: { value: value.trim() } })
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor="identifier-input" className="text-title-md">
          Check a UPI ID, phone number or website <span className="hi text-body-sm font-normal text-ink-2" lang="hi">· यूपीआई आईडी या नंबर जाँचें</span>
        </label>
        <SampleButton onUse={() => setValue(SAMPLES.identifier)} />
      </div>
      <div className="relative mt-2">
        <input id="identifier-input" value={value} onChange={(event) => setValue(event.target.value)} placeholder="name@ybl · 98XXXXXXXX · example.in" className={`${inputClass} font-mono pr-32`} />
        {found && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2">
            <IdentifierChip type={found.type} value={found.type} copy={false} />
          </span>
        )}
      </div>
      <p className="mt-2 text-body-sm text-ink-2">
        PARAKH looks for it in officer-verified police cases and the reviewed blacklist. Nothing about your search is stored.
      </p>
      <Button type="submit" size="lg" icon="manage_search" className="mt-4" loading={check.isPending} disabled={value.trim().length < 3}>
        Check
      </Button>
    </form>
  )
}

function AnalysingPanel() {
  // Honest progress: the request is in flight; no invented counters or timings.
  return (
    <Card className="p-6" aria-live="polite">
      <p className="text-label-ui uppercase text-primary">Checking</p>
      <h2 className="text-headline-sm">Analysing… <span className="hi text-body-md font-normal text-ink-2" lang="hi">विश्लेषण हो रहा है</span></h2>
      <div className="mt-5">
        <Stepper
          label="Analysis progress"
          steps={[
            { label: 'Read your input', hindi: 'इनपुट पढ़ा', status: 'done' },
            { label: 'Check links & numbers', hindi: 'लिंक व नंबर', status: 'current' },
            { label: 'Match scam patterns', hindi: 'पैटर्न मिलान', status: 'current' },
            { label: 'Prepare the answer', hindi: 'उत्तर तैयार', status: 'todo' },
          ]}
        />
      </div>
    </Card>
  )
}

function SafetyPanel() {
  const rules = [
    ['password', 'Never share an OTP, PIN or CVV', 'ओटीपी, पिन या सीवीवी कभी न बताएँ'],
    ['payments', 'Receiving money never needs a UPI PIN', 'पैसे पाने के लिए पिन नहीं लगता'],
    ['android', 'Banks never send apps (.apk) by message', 'बैंक संदेश से ऐप नहीं भेजते'],
    ['local_police', 'There is no “digital arrest” in law', 'डिजिटल अरेस्ट जैसा कुछ नहीं होता'],
  ]
  return (
    <aside className="space-y-4">
      <Card className="p-5">
        <h2 className="flex items-center gap-2 text-title-md">
          <Icon name="health_and_safety" className="text-primary" /> Safety reminders
        </h2>
        <ul className="mt-3 space-y-3">
          {rules.map(([icon, text, hindi]) => (
            <li key={text} className="flex gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-accent-tint text-accent-strong"><Icon name={icon} size={20} /></span>
              <span className="text-body-sm text-ink">
                {text}
                <span className="hi block text-ink-3" lang="hi">{hindi}</span>
              </span>
            </li>
          ))}
        </ul>
      </Card>
      <div className="rounded-card bg-risk-high-ink p-5 text-white shadow-l2">
        <p className="text-label-ui uppercase text-white/80">Golden hour</p>
        <h2 className="text-headline-sm">Already lost money?</h2>
        <p className="hi mt-1 text-body-sm text-white/90" lang="hi">तुरंत 1930 पर कॉल करें।</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <a href="tel:1930" className="inline-flex h-11 items-center gap-2 rounded-chip bg-white px-4 font-semibold text-risk-high-ink">
            <Icon name="call" /> Call 1930
          </a>
          <ButtonLink to="/rescue" variant="ghost" className="border-white/40 bg-transparent text-white hover:bg-white/10 hover:text-white">Rescue guide</ButtonLink>
        </div>
      </div>
    </aside>
  )
}

export function CheckPage() {
  const [params, setParams] = useSearchParams()
  const requested = params.get('mode')
  const mode = MODES.some((item) => item.value === requested) ? requested : 'message'
  const check = useCheck()
  // Learn → "Check this example" passes the text in router state (never the URL).
  const { state } = useLocation()
  const prefill = typeof state?.text === 'string' ? state.text.slice(0, 5000) : ''

  return (
    <div className="mx-auto max-w-[1280px] px-4 py-8 md:px-8">
      <h1 className="text-headline-lg-mobile md:text-headline-lg">
        Check something suspicious <span className="hi block text-accent-strong md:inline" lang="hi">/ कुछ संदिग्ध जाँचें</span>
      </h1>
      <p className="mt-1 max-w-3xl text-body-md text-ink-2">
        Paste or upload what you received. PARAKH explains the risk in plain language. Nothing is stored.
      </p>
      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Segmented label="What do you want to check?" value={mode} onChange={(value) => setParams({ mode: value }, { replace: true })} options={MODES} />
        <ButtonLink to="/apk" variant="ghost" size="sm" icon="android">App (.apk)</ButtonLink>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="min-w-0 space-y-4">
          {check.isPending ? (
            <AnalysingPanel />
          ) : (
            <Card className="p-5 md:p-6">
              {mode === 'message' && <MessageMode check={check} initialText={prefill} />}
              {mode === 'link' && <LinkMode check={check} />}
              {mode === 'email' && <EmailMode check={check} />}
              {(mode === 'screenshot' || mode === 'voice') && <MediaMode key={mode} kind={mode} check={check} />}
              {mode === 'qr' && <QrMode check={check} />}
              {mode === 'identifier' && <IdentifierMode check={check} />}
            </Card>
          )}
          {check.isError && (
            <div role="alert" className="flex items-start gap-3 rounded-card border border-risk-high/30 bg-risk-high-bg p-4 text-body-sm text-risk-high-ink">
              <Icon name="error" filled />
              <div>
                <p className="font-semibold">The check could not be completed.</p>
                <p>{check.error.message}</p>
              </div>
            </div>
          )}
        </div>
        <SafetyPanel />
      </div>
    </div>
  )
}

export default CheckPage
