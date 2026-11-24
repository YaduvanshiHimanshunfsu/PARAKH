import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Button, ButtonLink, Card, CardHeader, FileDrop, Icon, IdentifierChip, RiskBadge, RiskGauge, Segmented, Stepper } from '../../../design/ui'
import { riskMeta } from '../../../design/vocab'
import { citizenApi } from '../../../lib/api'

// Built from design/stitch/parakh_app_check_apk_forensic_scanner. The file is
// parsed statically on the server (manifest, signing certificate, embedded
// strings). It is never installed or executed, and it is not stored.

const MAX_BYTES = 50 * 1024 * 1024

const LEVEL_INFO = {
  SPECIAL: ['Special access', 'Can control the phone or read other apps — rarely needed.', 'HIGH'],
  DANGEROUS: ['Sensitive', 'Reads personal data such as SMS, contacts or location.', 'MEDIUM'],
  NORMAL: ['Normal', 'Low-risk access most apps need.', 'LOW'],
  UNKNOWN: ['Other', 'Not in PARAKH’s reference list.', 'UNKNOWN'],
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function IdentityCard({ details }) {
  const cert = details.certificate || {}
  const rows = [
    ['App name', details.app_label || 'Not declared'],
    ['Package', details.package || 'Unreadable'],
    ['Version', [details.version_name, details.version_code && `(${details.version_code})`].filter(Boolean).join(' ') || '—'],
    ['Target Android API', details.target_sdk ?? '—'],
    ['File size', formatBytes(details.size_bytes)],
    ['Components', `${details.activity_count ?? 0} screens · ${details.service_count ?? 0} services · ${details.receiver_count ?? 0} receivers`],
  ]
  return (
    <Card className="p-5">
      <CardHeader title="App identity" hindi="ऐप की पहचान" />
      <dl className="mt-3 grid gap-x-6 gap-y-2 text-body-sm sm:grid-cols-2">
        {rows.map(([name, value]) => (
          <div key={name} className="min-w-0">
            <dt className="text-label-ui uppercase text-ink-3">{name}</dt>
            <dd className="break-all font-mono text-ink">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-4 rounded-chip bg-canvas p-3 text-body-sm">
        <p className="text-label-ui uppercase text-ink-3">Signing certificate</p>
        <p className="mt-1 break-words text-ink">{cert.subject || 'No readable signature'}</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {cert.debug_certificate && (
            <span className="inline-flex items-center gap-1 font-semibold text-risk-high-ink">
              <Icon name="gpp_maybe" size={16} filled /> Signed with a debug (test) certificate
            </span>
          )}
          {cert.self_signed && !cert.debug_certificate && <span className="text-ink-2">Self-signed (normal for Android, but the signer is unverified)</span>}
          {Number.isFinite(cert.validity_days) && <span className="text-ink-2">· valid for {Math.round(cert.validity_days / 365)} years</span>}
        </div>
        {cert.sha256 && <p className="mt-2 break-all font-mono text-[11px] text-ink-3">SHA-256 {cert.sha256}</p>}
      </div>
      {details.sha256 && <p className="mt-2 break-all font-mono text-[11px] text-ink-3">File SHA-256 {details.sha256}</p>}
    </Card>
  )
}

function Permissions({ profile }) {
  const groups = useMemo(() => {
    const out = { SPECIAL: [], DANGEROUS: [], NORMAL: [], UNKNOWN: [] }
    for (const row of profile || []) (out[row.level] || out.UNKNOWN).push(row)
    return out
  }, [profile])
  const firstNonEmpty = ['SPECIAL', 'DANGEROUS', 'NORMAL', 'UNKNOWN'].find((key) => groups[key].length) || 'SPECIAL'
  const [tab, setTab] = useState(firstNonEmpty)
  if (!profile?.length) {
    return (
      <Card className="p-5">
        <CardHeader title="Permissions" hindi="अनुमतियाँ" />
        <p className="mt-2 text-body-sm text-ink-2">This app asks for no permissions, or its manifest could not be read.</p>
      </Card>
    )
  }
  return (
    <Card className="p-5">
      <CardHeader title={`Permissions (${profile.length})`} hindi="ऐप क्या-क्या कर सकता है" />
      <Segmented
        className="mt-3"
        size="sm"
        label="Permission level"
        value={tab}
        onChange={setTab}
        options={Object.keys(groups).map((key) => ({ value: key, label: `${LEVEL_INFO[key][0]} · ${groups[key].length}` }))}
      />
      <p className="mt-2 text-body-sm text-ink-2">{LEVEL_INFO[tab][1]}</p>
      <ul className="mt-3 divide-y divide-line-soft">
        {groups[tab].map((row) => (
          <li key={row.name} className="flex items-start gap-3 py-2">
            <RiskBadge level={LEVEL_INFO[row.level]?.[2] || 'UNKNOWN'} className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="break-all font-mono text-body-sm font-semibold text-ink">{row.short}</p>
              <p className="text-body-sm text-ink-2">
                <span className="text-ink-3">{row.category} · </span>
                {row.description}
              </p>
            </div>
          </li>
        ))}
        {!groups[tab].length && <li className="py-2 text-body-sm text-ink-3">None in this group.</li>}
      </ul>
    </Card>
  )
}

function Findings({ findings }) {
  if (!findings.length) return null
  const order = { HIGH: 0, MEDIUM: 1, LOW: 2 }
  const sorted = [...findings].sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3))
  return (
    <Card className="p-5">
      <CardHeader title="What PARAKH found" hindi="क्या मिला" />
      <ul className="mt-3 space-y-3">
        {sorted.map((finding, index) => (
          <li key={`${finding.code}-${index}`} className="flex gap-3">
            <RiskBadge level={finding.severity} className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="text-body-md text-ink">{finding.explanation}</p>
              {finding.evidence && <p className="mt-0.5 break-all font-mono text-body-sm text-ink-3">{finding.evidence}</p>}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  )
}

function ApkResult({ result, onReset }) {
  const meta = riskMeta(result.risk_level)
  const details = result.details || {}
  const hidden = (result.identifiers || []).filter((item) => !['PACKAGE', 'CERT_SHA256', 'ICON_PHASH'].includes(item.type))
  return (
    <div className="space-y-5">
      <section className="rounded-hero border p-5 shadow-l2 md:p-7" style={{ background: meta.bg, borderColor: `color-mix(in srgb, ${meta.line} 35%, white)` }}>
        <div className="flex flex-col gap-5 md:flex-row md:items-center">
          <div className="min-w-0 flex-1">
            <p className="text-label-ui uppercase text-ink-2">
              <Icon name="android" size={16} /> {details.filename || 'APK file'}
            </p>
            <h2 className="mt-1 text-headline-lg-mobile md:text-headline-lg" style={{ color: meta.ink }}>
              {result.risk_level === 'HIGH' ? 'Do not install this app' : result.risk_level === 'MEDIUM' ? 'Be careful with this app' : 'No strong danger signs found'}
            </h2>
            <p className="hi text-body-lg" lang="hi" style={{ color: meta.ink }}>
              {result.risk_level === 'HIGH' ? 'यह ऐप इंस्टॉल न करें' : result.risk_level === 'MEDIUM' ? 'इस ऐप से सावधान रहें' : 'खतरे के बड़े संकेत नहीं मिले'}
            </p>
            <p className="mt-3 max-w-2xl text-body-md text-ink">{result.summary}</p>
          </div>
          <div className="flex shrink-0 justify-center rounded-card bg-white/70 p-4">
            <RiskGauge value={result.risk_score} level={result.risk_level} caption="Risk score" />
          </div>
        </div>
      </section>

      {result.reported_identifiers?.length > 0 && (
        <div role="alert" className="rounded-card border border-risk-high/30 bg-risk-high-bg p-4">
          <p className="flex items-center gap-2 text-title-md text-risk-high-ink">
            <Icon name="history" filled /> Already seen in police cases
          </p>
          <p className="mt-1 text-body-sm text-ink-2">Details inside this app match officer-verified fraud cases:</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {result.reported_identifiers.map((item) => (
              <IdentifierChip key={`${item.type}:${item.value}`} type={item.type} value={item.value} count={item.case_count} />
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <div className="min-w-0 space-y-5">
          <Findings findings={result.findings || []} />
          <Permissions profile={details.permission_profile} />
          {hidden.length > 0 && (
            <Card className="p-5">
              <CardHeader title="Hidden details inside the app" hindi="ऐप के अंदर छिपी जानकारी" />
              <p className="mt-1 text-body-sm text-ink-2">Payment IDs, numbers, links and servers written into the app’s code.</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {hidden.slice(0, 40).map((item) => (
                  <IdentifierChip key={`${item.type}:${item.value}`} type={item.type} value={item.value} />
                ))}
              </div>
            </Card>
          )}
          <IdentityCard details={details} />
        </div>
        <aside className="space-y-4">
          {result.advice?.length > 0 && (
            <Card className="p-5">
              <CardHeader title="What to do" hindi="क्या करें" />
              <ol className="mt-3 space-y-2">
                {result.advice.map((step) => (
                  <li key={step} className="flex gap-2 text-body-md text-ink">
                    <Icon name="check_circle" filled size={20} className="mt-0.5 shrink-0 text-risk-low" /> {step}
                  </li>
                ))}
              </ol>
            </Card>
          )}
          <div className="rounded-card bg-risk-high-ink p-5 text-white shadow-l2">
            <h2 className="text-title-md">Already installed it?</h2>
            <p className="mt-1 text-body-sm text-white/90">Switch on flight mode, uninstall it, and call your bank and {result.helpline}.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <a href={`tel:${result.helpline}`} className="inline-flex h-10 items-center gap-1.5 rounded-chip bg-white px-4 text-body-sm font-semibold text-risk-high-ink">
                <Icon name="call" size={18} /> Call {result.helpline}
              </a>
              <ButtonLink to="/rescue?exposure=INSTALLED_APP_OR_SCREEN_SHARE" variant="ghost" size="sm" className="border-white/40 bg-transparent text-white hover:bg-white/10 hover:text-white">
                Rescue plan
              </ButtonLink>
            </div>
          </div>
          {details.limitations?.length > 0 && (
            <div className="rounded-card border border-line bg-surface-container-low p-4 text-body-sm text-ink-2">
              <p className="font-semibold text-ink">Limits of this check</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-5">
                {details.limitations.map((item) => <li key={item}>{item}</li>)}
                <li>The app was read, not run. A clean result does not prove an app is safe.</li>
              </ul>
            </div>
          )}
          <Button variant="ghost" block icon="restart_alt" onClick={onReset}>Check another app</Button>
        </aside>
      </div>
    </div>
  )
}

export function ApkPage() {
  const [file, setFile] = useState(null)
  const [tooBig, setTooBig] = useState(false)
  const analyse = useMutation({ mutationFn: (picked) => citizenApi.analyseApk(picked) })

  function pick(picked) {
    setTooBig(false)
    if (picked.size > MAX_BYTES) {
      setTooBig(true)
      return
    }
    setFile(picked)
    analyse.mutate(picked)
  }

  return (
    <div className="mx-auto max-w-[1280px] px-4 py-8 md:px-8">
      <h1 className="text-headline-lg-mobile md:text-headline-lg">
        Check an app before you install it <span className="hi block text-accent-strong md:inline" lang="hi">/ इंस्टॉल से पहले ऐप जाँचें</span>
      </h1>
      <p className="mt-1 max-w-3xl text-body-md text-ink-2">
        Got an .apk on WhatsApp — an “e-challan”, “bank KYC” or “electricity bill” app? Banks and police never send apps this way. Drop it here and PARAKH reads what it can do.
      </p>

      <div className="mt-6">
        {analyse.isSuccess ? (
          <ApkResult
            result={analyse.data}
            onReset={() => {
              analyse.reset()
              setFile(null)
            }}
          />
        ) : analyse.isPending ? (
          <Card className="p-6" aria-live="polite">
            <p className="text-label-ui uppercase text-primary">Reading {file?.name}</p>
            <h2 className="text-headline-sm">Analysing the app… <span className="hi text-body-md font-normal text-ink-2" lang="hi">ऐप पढ़ा जा रहा है</span></h2>
            <div className="mt-5">
              <Stepper
                label="APK analysis"
                steps={[
                  { label: 'Upload', hindi: 'अपलोड', status: 'done' },
                  { label: 'Manifest & permissions', hindi: 'अनुमतियाँ', status: 'current' },
                  { label: 'Signature & hidden strings', hindi: 'हस्ताक्षर', status: 'current' },
                  { label: 'Match police cases', hindi: 'केस मिलान', status: 'todo' },
                ]}
              />
            </div>
          </Card>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
            <div className="min-w-0 space-y-4">
              <FileDrop accept=".apk,application/vnd.android.package-archive" icon="android" title="Drop the .apk file" hint="Up to 50 MB · the app is read, never installed or run, and not stored" onFile={pick} />
              {tooBig && <p role="alert" className="text-body-sm text-risk-high-ink">That file is larger than 50 MB. PARAKH checks files up to 50 MB.</p>}
              {analyse.isError && (
                <div role="alert" className="flex items-start gap-3 rounded-card border border-risk-high/30 bg-risk-high-bg p-4 text-body-sm text-risk-high-ink">
                  <Icon name="error" filled />
                  <div>
                    <p className="font-semibold">The app could not be analysed.</p>
                    <p>{analyse.error.message}</p>
                  </div>
                </div>
              )}
            </div>
            <Card className="p-5">
              <CardHeader title="What PARAKH looks at" hindi="क्या जाँचा जाता है" />
              <ul className="mt-3 space-y-3 text-body-sm text-ink">
                {[
                  ['sms', 'Permissions to read SMS, OTPs, contacts or the screen'],
                  ['verified', 'Who signed the app, and whether it is a test certificate'],
                  ['account_balance', 'Bank or government names it pretends to be'],
                  ['qr_code_2', 'UPI IDs, phone numbers, Telegram links and servers hidden inside'],
                  ['history', 'Whether those details appear in police cases'],
                ].map(([icon, text]) => (
                  <li key={text} className="flex gap-3">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary-tint text-primary"><Icon name={icon} size={18} /></span>
                    {text}
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}

export default ApkPage
