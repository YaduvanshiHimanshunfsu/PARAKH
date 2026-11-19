import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileUp, Globe, MessageSquare } from 'lucide-react'
import * as api from '../../lib/investigateApi'
import { ErrorNote } from '../../features/investigate/ui'

const TABS = [
  ['text', 'Message, URL or email', MessageSquare],
  ['apk', 'Android app (.apk)', FileUp],
  ['website', 'Website', Globe],
]

export function SubmitPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('text')
  const [artifactType, setArtifactType] = useState('MESSAGE')
  const [content, setContent] = useState('')
  const [url, setUrl] = useState('')
  const [file, setFile] = useState(null)
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      let created
      if (tab === 'text') {
        created = await api.submitArtifact({
          artifact_type: artifactType,
          content: content.trim(),
          reporter_note: note.trim() || undefined,
        })
      } else if (tab === 'apk') {
        if (!file) throw new Error('Choose an APK file to analyse.')
        created = await api.uploadApk(file, note.trim() || undefined)
      } else {
        created = await api.analyseWebsite({
          url: url.trim(),
          reporter_note: note.trim() || undefined,
        })
      }
      navigate(`/investigate/case/${created.case_id}`)
    } catch (caught) {
      setError(caught.message)
    } finally {
      setBusy(false)
    }
  }

  const canSubmit =
    (tab === 'text' && content.trim().length >= 3) ||
    (tab === 'apk' && file) ||
    (tab === 'website' && url.trim().length >= 4)

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">New analysis</h1>
        <p className="text-sm text-slate-500">
          Analysis opens a case, extracts identifiers, and links it to anything already on record.
        </p>
      </div>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Artifact type">
        {TABS.map(([key, label, Icon]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => {
              setTab(key)
              setError('')
            }}
            className={`flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-semibold transition ${
              tab === key
                ? 'bg-blue-600 text-white shadow-sm'
                : 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
            }`}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <ErrorNote message={error} />

        {tab === 'text' && (
          <>
            <div>
              <label htmlFor="type" className="mb-1 block text-xs font-bold text-slate-700">
                Content type
              </label>
              <select
                id="type"
                value={artifactType}
                onChange={(event) => setArtifactType(event.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="MESSAGE">SMS / WhatsApp / social message</option>
                <option value="URL">URL (structure, domain age, redirects)</option>
                <option value="EMAIL">Email body or raw .eml</option>
              </select>
            </div>
            <div>
              <label htmlFor="content" className="mb-1 block text-xs font-bold text-slate-700">
                Content
              </label>
              <textarea
                id="content"
                rows={9}
                value={content}
                onChange={(event) => setContent(event.target.value)}
                placeholder="Paste the suspicious message, link, or raw email here…"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </div>
          </>
        )}

        {tab === 'apk' && (
          <div>
            <label htmlFor="apk" className="mb-1 block text-xs font-bold text-slate-700">
              APK file
            </label>
            <input
              id="apk"
              type="file"
              accept=".apk,application/vnd.android.package-archive"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-xs file:font-semibold"
            />
            <p className="mt-2 text-xs text-slate-500">
              Static inspection only — permissions, embedded URLs, certificate and icon. The app is
              never installed or executed.
            </p>
          </div>
        )}

        {tab === 'website' && (
          <div>
            <label htmlFor="url" className="mb-1 block text-xs font-bold text-slate-700">
              Website address
            </label>
            <input
              id="url"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://example-investment-site.test/join"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
            />
            <p className="mt-2 text-xs text-slate-500">
              The page is fetched as text to read its content and extract payment identifiers. No
              JavaScript is executed and no form is submitted.
            </p>
          </div>
        )}

        <div>
          <label htmlFor="note" className="mb-1 block text-xs font-bold text-slate-700">
            Officer note <span className="font-normal text-slate-400">(optional)</span>
          </label>
          <input
            id="note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Complaint reference, source, or context"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
          />
        </div>

        <button
          type="submit"
          disabled={busy || !canSubmit}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {busy ? 'Analysing…' : 'Analyse and open case'}
        </button>
      </form>
    </div>
  )
}
