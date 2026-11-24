// Shared vocabulary for the action layer. Labels match the backend enums in
// app/schemas.py and app/data/approval_policy.py.

export const DOC_META = {
  BANK_PRODUCE_94: { short: 'Bank records', icon: 'account_balance', law: 'BNSS s.94' },
  BANK_FREEZE_106: { short: 'Freeze funds', icon: 'lock', law: 'BNSS s.106' },
  TELECOM_CAF_CDR: { short: 'Telecom records', icon: 'sim_card', law: 'BNSS s.94' },
  DOT_CHAKSHU_REPORT: { short: 'Report number', icon: 'report', law: 'Sanchar Saathi' },
  REGISTRAR_TAKEDOWN: { short: 'Domain takedown', icon: 'language', law: 'IT Act s.79(3)(b)' },
  HOSTING_ABUSE: { short: 'Hosting abuse', icon: 'dns', law: 'IT Act s.79(3)(b)' },
  INTERMEDIARY_79_3B: { short: 'Platform takedown', icon: 'hub', law: 'IT Act s.79(3)(b)' },
  BSA_63_CERT: { short: 'Evidence certificate', icon: 'verified', law: 'BSA s.63' },
}

export const STATUS_META = {
  DRAFT: { label: 'Draft', tone: 'bg-canvas text-ink-2', help: 'Not submitted yet.' },
  RETURNED: { label: 'Returned', tone: 'bg-risk-medium-bg text-risk-medium-ink', help: 'Sent back for correction.' },
  PENDING_STATION: { label: 'With SHO', tone: 'bg-primary-tint text-primary', help: 'Awaiting station approval.' },
  PENDING_SUPERVISOR: { label: 'With supervisor', tone: 'bg-primary-tint text-primary', help: 'Awaiting district approval.' },
  APPROVED: { label: 'Approved', tone: 'bg-risk-low-bg text-risk-low-ink', help: 'Ready to dispatch.' },
  DISPATCHED: { label: 'Dispatched', tone: 'bg-accent-tint text-accent-strong', help: 'Sent; awaiting a reply.' },
  RESPONDED: { label: 'Answered', tone: 'bg-risk-low-bg text-risk-low-ink', help: 'A reply has been recorded.' },
  CLOSED: { label: 'Closed', tone: 'bg-canvas text-ink-3', help: 'Finished.' },
  CANCELLED: { label: 'Cancelled', tone: 'bg-canvas text-ink-3', help: 'Withdrawn with a reason.' },
}

export const CHANNELS = [
  { value: 'EMAIL', label: 'Email' },
  { value: 'PORTAL', label: 'Portal' },
  { value: 'POST', label: 'Post' },
  { value: 'HAND', label: 'By hand' },
]

export function docMeta(type) {
  return DOC_META[type] || { short: type, icon: 'description', law: '' }
}

export function statusMeta(status) {
  return STATUS_META[status] || { label: status, tone: 'bg-canvas text-ink-2', help: '' }
}

/**
 * Which buttons this officer may use on this document.
 * The server decides for real; this only avoids offering an action that would
 * certainly be refused.
 */
export function allowedActions(document, role) {
  const status = document?.status
  const isApprover =
    (status === 'PENDING_STATION' && ['STATION_HEAD', 'SUPERVISOR', 'ADMIN', 'OFFICER'].includes(role)) ||
    (status === 'PENDING_SUPERVISOR' && ['SUPERVISOR', 'ADMIN', 'OFFICER'].includes(role))
  return {
    edit: ['DRAFT', 'RETURNED'].includes(status),
    submit: ['DRAFT', 'RETURNED'].includes(status),
    approve: isApprover,
    return: isApprover,
    dispatch: status === 'APPROVED',
    respond: status === 'DISPATCHED',
    close: ['DISPATCHED', 'RESPONDED'].includes(status),
    cancel: !['CLOSED', 'CANCELLED'].includes(status),
  }
}

export function formatRupees(paise) {
  if (!paise) return '₹0'
  return `₹${(paise / 100).toLocaleString('en-IN')}`
}
