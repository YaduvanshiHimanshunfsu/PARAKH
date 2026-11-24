import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import { Button, ButtonLink, Card, Icon, IdentifierChip } from '../../../design/ui'
import { detectIdentifiers } from '../../../lib/identifiers'
import scams from '../../../content/scams.json'
import { useCheck } from '../useCheck'
import { HeroMap } from './HeroMap'

// Built from design/stitch/parakh_citizen_cyber_safety_portal (desktop) and
// parakh_citizen_mobile_home (< 768 px). Stitch claims removed per the H.1 honesty table
// (certifications, timing promises, audio forensics, invented counters).

const MODES = [
  { mode: 'message', label: 'Message', hindi: 'संदेश', icon: 'sms' },
  { mode: 'link', label: 'Link', hindi: 'लिंक', icon: 'link' },
  { mode: 'screenshot', label: 'Screenshot', hindi: 'स्क्रीनशॉट', icon: 'image_search' },
  { mode: 'qr', label: 'QR code', hindi: 'क्यूआर', icon: 'qr_code_scanner' },
  { mode: 'identifier', label: 'UPI / Phone', hindi: 'यूपीआई / फोन', icon: 'account_balance_wallet' },
]

const STEPS = [
  { icon: 'content_paste', title: 'Paste or upload', hindi: 'चिपकाएँ या अपलोड करें', body: 'An SMS, WhatsApp text, link, email, screenshot, QR code or an app file you received.' },
  { icon: 'manage_search', title: 'PARAKH reads it', hindi: 'परख जाँचता है', body: 'Links, phone numbers, UPI IDs and wallets are pulled out and checked.' },
  { icon: 'rule', title: 'Matches scam patterns', hindi: 'ठगी के पैटर्न', body: 'Reviewed rules for Indian scams, plus known cases from police records.' },
  { icon: 'verified_user', title: 'Clear verdict and next steps', hindi: 'स्पष्ट परिणाम और कदम', body: 'Low, medium or high risk with the exact reasons and what to do now.' },
]

const TILES = [
  { to: '/check?mode=message', icon: 'sms', title: 'SMS & WhatsApp', hindi: 'एसएमएस और व्हाट्सऐप', body: 'Bill cut-off, KYC block, lottery and job messages.' },
  { to: '/check?mode=link', icon: 'link', title: 'Links & websites', hindi: 'लिंक और वेबसाइट', body: 'Look-alike bank and government domains, short links.' },
  { to: '/apk', icon: 'android', title: 'Android apps (.apk)', hindi: 'एंड्रॉइड ऐप', body: 'Fake loan, e-challan and wedding-invite apps.' },
  { to: '/check?mode=screenshot', icon: 'image_search', title: 'Screenshots', hindi: 'स्क्रीनशॉट', body: 'Read the text from a screenshot, then check it.' },
  { to: '/check?mode=qr', icon: 'qr_code_scanner', title: 'QR codes', hindi: 'क्यूआर कोड', body: 'See whether a QR sends money out before you scan.' },
  { to: '/check?mode=email', icon: 'mail', title: 'Emails', hindi: 'ईमेल', body: 'Sender checks, spoofing and risky attachments.' },
  { to: '/check?mode=identifier', icon: 'account_balance_wallet', title: 'UPI ID or phone number', hindi: 'यूपीआई आईडी या फोन नंबर', body: 'Is it already in verified police cases?' },
]

function FadeIn({ children, delay = 0, className = '' }) {
  const reduce = useReducedMotion()
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.4, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  )
}

function QuickCheck() {
  const [text, setText] = useState('')
  const navigate = useNavigate()
  const check = useCheck()
  const chips = detectIdentifiers(text).slice(0, 4)
  const looksLikeLink = /^\s*(https?:\/\/|www\.)\S+\s*$/i.test(text)

  function submit(event) {
    event.preventDefault()
    const value = text.trim()
    if (value.length < 3) return
    if (looksLikeLink) check.mutate({ kind: 'url', input: { url: value } })
    else check.mutate({ kind: 'message', input: { text: value, language: 'auto' } })
  }

  return (
    <form onSubmit={submit} className="glass mt-6 rounded-hero p-4 shadow-l2 md:p-5">
      <label htmlFor="quick-check" className="text-label-ui uppercase text-ink-2">
        Paste a suspicious message or link
        <span className="hi ml-1 normal-case text-ink-3" lang="hi">· संदिग्ध संदेश या लिंक चिपकाएँ</span>
      </label>
      <textarea
        id="quick-check"
        value={text}
        onChange={(event) => setText(event.target.value)}
        rows={3}
        maxLength={5000}
        placeholder="e.g. Dear consumer, your electricity will be disconnected tonight…"
        className="mt-2 w-full resize-none rounded-chip border-[1.5px] border-line bg-white p-3 text-body-md outline-none focus:border-primary"
      />
      {chips.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5" aria-label="Detected in your text">
          {chips.map((chip) => (
            <IdentifierChip key={`${chip.type}:${chip.value}`} type={chip.type} value={chip.value} copy={false} />
          ))}
        </div>
      )}
      {check.isError && (
        <p role="alert" className="mt-2 text-body-sm text-risk-high-ink">
          {check.error.message}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button type="submit" size="lg" icon="search_check" loading={check.isPending} disabled={text.trim().length < 3}>
          Check now <span className="hi font-normal" lang="hi">/ तुरंत जाँचें</span>
        </Button>
        <div className="flex flex-wrap gap-1.5">
          {MODES.map((mode) => (
            <button
              key={mode.mode}
              type="button"
              onClick={() => navigate(`/check?mode=${mode.mode}`)}
              className="inline-flex h-9 items-center gap-1 rounded-chip border border-line bg-white px-2.5 text-body-sm font-semibold text-ink-2 hover:border-primary hover:text-primary"
            >
              <Icon name={mode.icon} size={17} />
              {mode.label}
            </button>
          ))}
        </div>
      </div>
      <ul className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-body-sm text-ink-2">
        <li className="flex items-center gap-1"><Icon name="lock" size={16} /> No login needed</li>
        <li className="flex items-center gap-1"><Icon name="shield_lock" size={16} /> Nothing is stored</li>
        <li className="flex items-center gap-1"><Icon name="translate" size={16} /> Hindi &amp; English</li>
        <li className="flex items-center gap-1"><Icon name="cloud_off" size={16} /> Works without the AI service</li>
      </ul>
    </form>
  )
}

export function HomePage() {
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div aria-hidden="true" className="pointer-events-none absolute -right-40 -top-40 h-[520px] w-[520px] rounded-full bg-[radial-gradient(circle,#e0e7ff_0%,transparent_70%)]" />
        <div className="relative mx-auto grid max-w-[1280px] items-center gap-8 px-4 pb-12 pt-8 md:px-8 lg:grid-cols-[1.05fr_1fr] lg:pt-14">
          <div className="min-w-0">
            <p className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1 text-label-ui uppercase text-primary">
              <Icon name="shield" filled size={15} /> Rajasthan Police · Citizen cyber safety
            </p>
            <h1 className="mt-4 text-display-hero-mobile md:text-display-hero">
              Got a suspicious message?{' '}
              <span className="hi block text-accent-strong" lang="hi">
                परखो, फिर भरोसो।
              </span>
            </h1>
            <p className="mt-3 max-w-xl text-body-lg text-ink-2">
              Check SMS, WhatsApp messages, links, QR codes, emails and Android apps before you trust them. You get the
              exact reasons and what to do next.
            </p>
            <QuickCheck />
          </div>
          <HeroMap />
        </div>
      </section>

      {/* Pipeline */}
      <section className="mx-auto max-w-[1280px] px-4 py-12 md:px-8">
        <FadeIn>
          <p className="text-label-ui uppercase text-accent-strong">How it works</p>
          <h2 className="text-headline-lg-mobile md:text-headline-lg">Four steps from doubt to a clear answer</h2>
          <p className="hi text-body-md text-ink-2" lang="hi">संदेह से स्पष्ट उत्तर तक चार चरण</p>
        </FadeIn>
        <ol className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, index) => (
            <FadeIn key={step.title} delay={index * 0.06}>
              <li className="h-full rounded-card border border-line bg-card p-5 shadow-l1">
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-primary-tint text-primary">
                  <Icon name={step.icon} size={22} />
                </span>
                <p className="mt-3 text-label-ui uppercase text-ink-3">Step {index + 1}</p>
                <h3 className="text-title-md">{step.title}</h3>
                <p className="hi text-body-sm text-accent-strong" lang="hi">{step.hindi}</p>
                <p className="mt-2 text-body-sm text-ink-2">{step.body}</p>
              </li>
            </FadeIn>
          ))}
        </ol>
      </section>

      {/* What can you check */}
      <section className="bg-sand py-12">
        <div className="mx-auto max-w-[1280px] px-4 md:px-8">
          <FadeIn>
            <h2 className="text-headline-lg-mobile md:text-headline-lg">What can you check?</h2>
            <p className="hi text-body-md text-ink-2" lang="hi">आप क्या-क्या जाँच सकते हैं?</p>
          </FadeIn>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {TILES.map((tile, index) => (
              <FadeIn key={tile.title} delay={index * 0.04}>
                <Link
                  to={tile.to}
                  className="group flex h-full flex-col rounded-card border border-line bg-card p-5 shadow-l1 transition hover:-translate-y-0.5 hover:shadow-l2"
                >
                  <span className="grid h-11 w-11 place-items-center rounded-xl bg-accent-tint text-accent-strong">
                    <Icon name={tile.icon} size={22} />
                  </span>
                  <h3 className="mt-3 text-title-md group-hover:text-primary">{tile.title}</h3>
                  <p className="hi text-body-sm text-ink-3" lang="hi">{tile.hindi}</p>
                  <p className="mt-2 text-body-sm text-ink-2">{tile.body}</p>
                  <span className="mt-auto pt-3 text-body-sm font-semibold text-primary">Check now →</span>
                </Link>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>

      {/* Threat patterns */}
      <section className="mx-auto max-w-[1280px] px-4 py-12 md:px-8">
        <FadeIn className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-label-ui uppercase text-accent-strong">Rajasthan cyber advisory</p>
            <h2 className="text-headline-lg-mobile md:text-headline-lg">Scams to watch out for</h2>
            <p className="hi text-body-md text-ink-2" lang="hi">इन ठगी के तरीकों से सावधान रहें</p>
          </div>
          <ButtonLink to="/learn" variant="ghost" iconRight="arrow_forward">All scam types</ButtonLink>
        </FadeIn>
        <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {scams.types.slice(0, 6).map((item, index) => (
            <FadeIn key={item.id} delay={index * 0.05}>
              <article className="flex h-full flex-col rounded-card border border-line bg-card p-5 shadow-l1">
                <div className="flex items-center justify-between gap-2">
                  <span className="rounded-md bg-risk-high-bg px-2 py-0.5 text-label-ui uppercase text-risk-high-ink">{item.tag}</span>
                  <Icon name={item.icon} className="text-accent-strong" />
                </div>
                <h3 className="mt-3 text-title-md">{item.title}</h3>
                <p className="hi text-body-sm text-ink-3" lang="hi">{item.hindi}</p>
                <blockquote className="mt-3 rounded-chip bg-canvas p-3 font-mono text-[12.5px] leading-5 text-ink-2">“{item.example}”</blockquote>
                <p className="mt-3 text-body-sm text-ink">
                  <span className="font-semibold text-risk-high-ink">Red flag: </span>
                  {item.red_flag}
                </p>
                <p className="mt-2 text-body-sm text-ink-2">
                  <span className="font-semibold text-risk-low-ink">Stay safe: </span>
                  {item.safety}
                </p>
              </article>
            </FadeIn>
          ))}
        </div>
        <p className="mt-3 text-body-sm text-ink-3">Examples are paraphrased from public police and CERT-In advisories.</p>
      </section>

      {/* Privacy */}
      <section className="mx-auto max-w-[1280px] px-4 pb-12 md:px-8">
        <Card tone="sand" className="p-6 md:p-8">
          <div className="grid items-center gap-6 md:grid-cols-[1fr_1.2fr]">
            <div>
              <p className="text-label-ui uppercase text-accent-strong">Your privacy</p>
              <h2 className="text-headline-md">Your check stays with you</h2>
              <p className="hi text-body-md text-ink-2" lang="hi">आपकी जाँच आपके पास ही रहती है</p>
              <p className="mt-2 text-body-md text-ink-2">
                What you check is analysed and the answer comes back to you. Nothing is saved, unless you choose
                “Report to police” and tick the consent box.
              </p>
              <ButtonLink to="/privacy" variant="ghost" size="sm" className="mt-4">How your data is handled</ButtonLink>
            </div>
            <ol className="flex flex-wrap items-center justify-center gap-3 text-center text-body-sm">
              {[
                ['mobile', 'Your device'],
                ['memory', 'Analysed in memory'],
                ['task_alt', 'Answer back to you'],
              ].map(([icon, label], index, list) => (
                <li key={label} className="flex items-center gap-3">
                  <span className="flex w-28 flex-col items-center gap-2 rounded-card border border-line bg-white p-3 shadow-l1">
                    <Icon name={icon} size={26} className="text-primary" />
                    {label}
                  </span>
                  {index < list.length - 1 && <Icon name="arrow_forward" className="text-ink-3" />}
                </li>
              ))}
            </ol>
          </div>
        </Card>
      </section>

      {/* Emergency */}
      <section className="mx-auto max-w-[1280px] px-4 pb-14 md:px-8">
        <div className="flex flex-wrap items-center justify-between gap-5 rounded-hero border border-line border-l-4 border-l-risk-high bg-card p-6 shadow-l2 md:p-8">
          <div className="max-w-2xl">
            <p className="text-label-ui uppercase text-risk-high-ink">Lost money?</p>
            <h2 className="text-headline-md">Act within the golden hour</h2>
            <p className="hi text-body-md text-accent-strong" lang="hi">पैसे कट गए? तुरंत 1930 पर कॉल करें।</p>
            <p className="mt-2 text-body-md text-ink-2">
              Calling 1930 quickly gives the best chance of the receiving account being frozen before the money moves.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <ButtonLink href="tel:1930" variant="danger" size="lg" icon="call">Call 1930</ButtonLink>
            <ButtonLink href="https://cybercrime.gov.in" target="_blank" rel="noreferrer" variant="ghost" size="lg" icon="open_in_new">
              cybercrime.gov.in
            </ButtonLink>
            <ButtonLink to="/rescue" variant="ghost" size="lg" icon="emergency">Rescue guide</ButtonLink>
          </div>
        </div>
      </section>
    </div>
  )
}

export default HomePage
