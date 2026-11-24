import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Button, Card, CardHeader, EmptyBlock, Icon, StateBlock } from '../../../design/ui'
import { citizenApi } from '../../../lib/api'

// Built from design/stitch/parakh_official_help_directory_organisation_verifier.
// The verifier calls POST /parakh/organisation/verify and the directory is
// GET /parakh/trusted-channels (app/data/trusted_channels.py), so every number
// and link shown comes from one reviewed server-side list. The Stitch bank
// hotline grid is left out: bank numbers change and are not in that list.

const EXAMPLE = 'This is SBI customer care. Your YONO account is blocked. Update PAN at sbi-yono-update.in or call 9876543210.'

const CATEGORY_ICON = {
  'Financial cyber fraud': 'currency_rupee',
  'Bank and payment safety': 'account_balance',
  'SIM loss or SIM fraud': 'sim_card',
  'Remote-access or screen-sharing app': 'screen_share',
  'Email phishing': 'mail',
  'Identity documents': 'badge',
  'Family support': 'family_restroom',
}

function Verifier() {
  const [text, setText] = useState('')
  const verify = useMutation({ mutationFn: () => citizenApi.verifyOrganisation(text.trim()) })
  const data = verify.data
  return (
    <Card className="p-5 md:p-6">
      <CardHeader title="Is this really from them?" hindi="क्या यह सच में उन्हीं का है?" eyebrow="Organisation verifier" />
      <p className="mt-2 text-body-md text-ink-2">
        Paste a message that claims to be from a bank, government office, police or courier. PARAKH tells you the official website and the safe way to check.
      </p>
      <form
        className="mt-4"
        onSubmit={(event) => {
          event.preventDefault()
          if (text.trim().length >= 3) verify.mutate()
        }}
      >
        <div className="flex items-center justify-between">
          <label htmlFor="org-text" className="text-title-md">Message or caller claim</label>
          <button type="button" onClick={() => setText(EXAMPLE)} className="inline-flex items-center gap-1 text-body-sm font-semibold text-primary hover:underline">
            <Icon name="science" size={16} /> Try a practice sample
          </button>
        </div>
        <textarea
          id="org-text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={4}
          maxLength={5000}
          placeholder="e.g. “This is the electricity department…”"
          className="mt-2 w-full resize-y rounded-chip border-[1.5px] border-line bg-white p-3 text-body-md outline-none focus:border-primary"
        />
        <Button type="submit" icon="verified" className="mt-3" loading={verify.isPending} disabled={text.trim().length < 3}>
          Verify
        </Button>
      </form>
      {verify.isError && <p role="alert" className="mt-3 text-body-sm text-risk-high-ink">{verify.error.message}</p>}
      {data && (
        <div className="mt-5 space-y-3" aria-live="polite">
          {data.claims.length === 0 ? (
            <p className="rounded-chip bg-canvas p-4 text-body-md text-ink-2">
              No known organisation was named in this text. If someone claims to be from an office, find its number yourself on the official website.
            </p>
          ) : (
            data.claims.map((claim) => (
              <div key={claim.claimed_organisation} className="rounded-card border border-line p-4">
                <p className="text-label-ui uppercase text-ink-3">Claims to be</p>
                <p className="text-title-md text-ink">{claim.claimed_organisation}</p>
                {claim.official_domains.length > 0 && (
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <span className="text-body-sm text-ink-2">Official website{claim.official_domains.length > 1 ? 's' : ''}:</span>
                    {claim.official_domains.map((domain) => (
                      <span key={domain} className="inline-flex items-center gap-1 rounded-chip bg-risk-low-bg px-2 py-0.5 font-mono text-body-sm text-risk-low-ink">
                        <Icon name="verified" size={14} filled /> {domain}
                      </span>
                    ))}
                  </div>
                )}
                <p className="mt-3 flex gap-2 text-body-sm text-ink">
                  <Icon name="warning" size={18} className="shrink-0 text-risk-medium-ink" /> {claim.risk_reason}
                </p>
                <p className="mt-2 flex gap-2 text-body-sm text-ink">
                  <Icon name="check_circle" size={18} className="shrink-0 text-risk-low" filled /> {claim.safe_instruction}
                </p>
              </div>
            ))
          )}
          <p className="text-body-sm text-ink-3">{data.notice}</p>
        </div>
      )}
    </Card>
  )
}

export function HelpPage() {
  const channels = useQuery({ queryKey: ['trusted-channels'], queryFn: citizenApi.trustedChannels, staleTime: 3_600_000 })
  return (
    <div className="mx-auto max-w-[1180px] px-4 py-8 md:px-8">
      <h1 className="text-headline-lg-mobile md:text-headline-lg">
        Official help <span className="hi block text-accent-strong md:inline" lang="hi">/ आधिकारिक सहायता</span>
      </h1>
      <p className="mt-1 max-w-3xl text-body-md text-ink-2">
        Verify who is really contacting you, and reach the right office through a channel you found yourself — never through a number in a suspicious message.
      </p>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <Verifier />
        <div className="space-y-3">
          <a href="tel:1930" className="flex items-center gap-4 rounded-card bg-risk-high-ink p-5 text-white shadow-l2">
            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-white/15"><Icon name="call" filled size={26} /></span>
            <span>
              <span className="block text-headline-sm">1930</span>
              <span className="text-body-sm text-white/90">National Cyber Crime Helpline · lost money to fraud</span>
            </span>
          </a>
          <a href="tel:112" className="flex items-center gap-4 rounded-card border border-line bg-card p-5 shadow-l1">
            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-primary-tint text-primary"><Icon name="local_police" size={26} /></span>
            <span>
              <span className="block text-headline-sm text-ink">112</span>
              <span className="text-body-sm text-ink-2">Emergency Response Support System · immediate danger</span>
            </span>
          </a>
        </div>
      </div>

      <section className="mt-10" aria-labelledby="directory">
        <h2 id="directory" className="text-headline-sm">
          Where to go for what <span className="hi text-body-md font-normal text-ink-2" lang="hi">किस काम के लिए कहाँ जाएँ</span>
        </h2>
        <div className="mt-4">
          <StateBlock
            query={channels}
            isEmpty={(data) => !data.length}
            empty={<EmptyBlock icon="contact_support" title="No channels listed" />}
          >
            {(data) => (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {data.map((channel) => (
                  <Card key={channel.title} className="flex flex-col p-5">
                    <span className="grid h-10 w-10 place-items-center rounded-lg bg-primary-tint text-primary">
                      <Icon name={CATEGORY_ICON[channel.category] || 'support_agent'} />
                    </span>
                    <p className="mt-3 text-label-ui uppercase text-ink-3">{channel.category}</p>
                    <h3 className="text-title-md text-ink">{channel.title}</h3>
                    <p className="mt-1 flex-1 text-body-sm text-ink-2">{channel.instruction}</p>
                    {(channel.phone || channel.official_url) && (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {channel.phone && (
                          <a href={`tel:${channel.phone}`} className="inline-flex h-9 items-center gap-1 rounded-chip bg-primary px-3 text-body-sm font-semibold text-white">
                            <Icon name="call" size={16} /> {channel.phone}
                          </a>
                        )}
                        {channel.official_url && (
                          <a href={channel.official_url} target="_blank" rel="noreferrer" className="inline-flex h-9 items-center gap-1 rounded-chip border border-line px-3 text-body-sm font-semibold text-primary">
                            <Icon name="open_in_new" size={16} /> {channel.official_url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                          </a>
                        )}
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </StateBlock>
        </div>
      </section>
    </div>
  )
}

export default HelpPage
