import { useState } from 'react'
import {
  Button,
  Card,
  CardHeader,
  ConsentCheckbox,
  Donut,
  EmptyBlock,
  ErrorBlock,
  FileDrop,
  IdentifierChip,
  KpiCard,
  LoadingBlock,
  Modal,
  RiskBadge,
  RiskCard,
  RiskGauge,
  Segmented,
  Stepper,
  Timeline,
  useToast,
} from '../design/ui'
import { ApiError } from '../lib/api'

// Dev-only kit gallery at /__states (excluded from production builds by the
// router). Replaces the Stitch "simulate state" toggles: every component and
// every empty/loading/error state can be reviewed here against design/stitch.
// Values below are labelled sample data for visual review only.

export default function StatesGallery() {
  const [mode, setMode] = useState('message')
  const [consent, setConsent] = useState(false)
  const [modal, setModal] = useState(false)
  const toast = useToast()

  return (
    <div className="mx-auto max-w-[1280px] space-y-8 px-4 py-8 md:px-8">
      <header>
        <p className="text-label-ui uppercase text-accent-strong">Development only · sample data</p>
        <h1 className="text-headline-lg">Component kit &amp; states gallery</h1>
      </header>

      <Card className="space-y-4 p-6">
        <CardHeader title="Buttons" />
        <div className="flex flex-wrap gap-3">
          <Button icon="search_check">Primary</Button>
          <Button variant="citizen" icon="campaign">Citizen action</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger" icon="call">Call 1930</Button>
          <Button variant="subtle">Subtle</Button>
          <Button loading>Analysing</Button>
        </div>
      </Card>

      <Card className="space-y-4 p-6">
        <CardHeader title="Identifier chips" hindi="पहचानकर्ता" />
        <div className="flex flex-wrap gap-2">
          <IdentifierChip type="UPI" value="richplan@ybl" count={5} />
          <IdentifierChip type="PHONE" value="+919812345670" />
          <IdentifierChip type="DOMAIN" value="sbi-verify-kyc.in" />
          <IdentifierChip type="URL" value="https://sbi-verify-kyc.in/urgent" />
          <IdentifierChip type="TELEGRAM" value="t.me/richplanofficial" />
          <IdentifierChip type="IP" value="45.133.1.9" />
          <IdentifierChip type="IFSC" value="SBIN0001428" />
          <IdentifierChip type="CRYPTO_ETH" value="0x5290…9ee7" />
          <IdentifierChip type="PACKAGE" value="com.quickcash.instantloan" />
          <IdentifierChip type="CERT_SHA256" value="9c1e…a07b" />
          <IdentifierChip type="EMAIL" value="support@richplan-invest.xyz" />
          <IdentifierChip type="BANK_ACCOUNT" value="918273645501" />
        </div>
      </Card>

      <Card className="space-y-4 p-6">
        <CardHeader title="Risk" />
        <div className="flex flex-wrap gap-2">
          <RiskBadge level="HIGH" score={92} />
          <RiskBadge level="MEDIUM" hindi />
          <RiskBadge level="SAFE" />
          <RiskBadge level={null} />
        </div>
        <div className="flex flex-wrap gap-6">
          <RiskGauge value={92} level="HIGH" caption="High risk" />
          <RiskGauge value={45} level="MEDIUM" caption="Medium risk" />
          <RiskGauge value={12} level="LOW" caption="Low risk" />
        </div>
        <RiskCard level="HIGH" title="High risk — likely a scam" hindiTitle="उच्च जोखिम — यह धोखाधड़ी हो सकती है">
          Example verdict container.
        </RiskCard>
        <RiskCard level="LOW" title="No strong scam signs found — still verify" hindiTitle="कोई स्पष्ट धोखाधड़ी संकेत नहीं — फिर भी जाँचें" />
      </Card>

      <Card className="space-y-4 p-6">
        <CardHeader title="Controls" />
        <Segmented
          label="Check mode"
          value={mode}
          onChange={setMode}
          options={[
            { value: 'message', label: 'Message', hindi: 'संदेश', icon: 'sms' },
            { value: 'link', label: 'Link', hindi: 'लिंक', icon: 'link' },
            { value: 'email', label: 'Email', icon: 'mail' },
            { value: 'qr', label: 'QR', icon: 'qr_code_scanner' },
            { value: 'apk', label: 'App', icon: 'android' },
          ]}
        />
        <ConsentCheckbox checked={consent} onChange={setConsent} hindi="मैं सहमत हूँ कि यह छवि केवल पाठ पढ़ने के लिए उपयोग होगी।">
          I agree this image is read only to extract text and is not stored.
        </ConsentCheckbox>
        <FileDrop accept=".apk" title="Drag & drop an .apk" hint="Never installed or run. Nothing is stored." onFile={(file) => toast(`Picked ${file.name}`)} />
        <div className="flex gap-3">
          <Button variant="ghost" onClick={() => setModal(true)}>Open modal</Button>
          <Button variant="ghost" onClick={() => toast('Saved to this device', 'success')}>Toast</Button>
          <Button variant="ghost" onClick={() => toast('The server could not be reached.', 'error')}>Error toast</Button>
        </div>
        <Modal open={modal} onClose={() => setModal(false)} title="Example dialog" footer={<Button onClick={() => setModal(false)}>OK</Button>}>
          Native dialog with focus trap and Esc to close.
        </Modal>
      </Card>

      <Card className="space-y-6 p-6">
        <CardHeader title="Flow" />
        <Stepper
          steps={[
            { label: 'Read message', hindi: 'संदेश पढ़ना', status: 'done' },
            { label: 'Check links & numbers', hindi: 'लिंक व नंबर', status: 'done' },
            { label: 'Match scam patterns', hindi: 'पैटर्न मिलान', status: 'current' },
            { label: 'Prepare answer', hindi: 'उत्तर तैयार', status: 'todo' },
          ]}
        />
        <Timeline
          items={[
            { id: 1, time: '02 Nov', title: 'SMS first seen', tone: 'primary' },
            { id: 2, time: '11 Nov', title: 'Variant: 10% → 12%', tone: 'medium' },
            { id: 3, time: '20 Nov', title: 'Phone rotated, same UPI ID', tone: 'high' },
          ]}
        />
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard label="Total cases" value={null} delta="loading" />
        <KpiCard label="High risk" hindi="उच्च जोखिम" value={18} tone="high" trend={[2, 3, 5, 4, 7, 9]} />
        <KpiCard label="Citizen reports to verify" value={4} tone="medium" />
      </div>
      <Card className="p-6">
        <Donut
          label="Artifact mix"
          segments={[
            { label: 'SMS', value: 9, color: '#2563eb' },
            { label: 'APK', value: 3, color: '#4f46e5' },
            { label: 'Website', value: 2, color: '#0d9488' },
            { label: 'URL', value: 2, color: '#475569' },
          ]}
        />
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="p-6">
          <LoadingBlock rows={5} />
        </Card>
        <Card>
          <EmptyBlock title="No cases match these filters">Try clearing a filter.</EmptyBlock>
        </Card>
        <Card>
          <ErrorBlock error={new ApiError(0, 'The PARAKH server could not be reached. Check that it is running.')} onRetry={() => toast('Retrying…')} />
        </Card>
      </div>
    </div>
  )
}
