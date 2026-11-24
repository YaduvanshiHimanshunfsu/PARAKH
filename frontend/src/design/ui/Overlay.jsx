import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Icon } from './Icon'

/** Modal dialog on the native <dialog> element (focus trap and Esc for free). */
export function Modal({ open, onClose, title, children, footer, width = 'max-w-lg' }) {
  const ref = useRef(null)
  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(event) => event.target === ref.current && onClose?.()}
      className={`w-[calc(100%-2rem)] ${width} rounded-hero border border-line bg-card p-0 text-ink shadow-l3 backdrop:bg-slate-900/30`}
    >
      <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
        <h2 className="text-headline-sm">{title}</h2>
        <button type="button" onClick={onClose} aria-label="Close" className="grid h-9 w-9 place-items-center rounded-lg hover:bg-canvas">
          <Icon name="close" />
        </button>
      </div>
      <div className="px-5 py-4">{children}</div>
      {footer && <div className="flex justify-end gap-2 border-t border-line px-5 py-3">{footer}</div>}
    </dialog>
  )
}

const ToastContext = createContext(null)

/** Lightweight toasts (replaces react-hot-toast). tone: info | success | error */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const dismiss = useCallback((id) => setToasts((list) => list.filter((toast) => toast.id !== id)), [])
  const push = useCallback(
    (message, tone = 'info') => {
      const id = Math.random().toString(36).slice(2)
      setToasts((list) => [...list.slice(-3), { id, message, tone }])
      setTimeout(() => dismiss(id), tone === 'error' ? 7000 : 4000)
    },
    [dismiss],
  )
  const icon = { info: 'info', success: 'check_circle', error: 'error' }
  const tone = {
    info: 'border-line text-ink',
    success: 'border-risk-low text-risk-low-ink',
    error: 'border-risk-high text-risk-high-ink',
  }
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-2 px-4 md:bottom-6">
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              className={`pointer-events-auto flex max-w-md items-start gap-2 rounded-chip border bg-card px-4 py-3 text-body-sm shadow-l3 ${tone[toast.tone]}`}
            >
              <Icon name={icon[toast.tone]} filled />
              <span className="text-ink">{toast.message}</span>
              <button type="button" onClick={() => dismiss(toast.id)} aria-label="Dismiss" className="ml-2 text-ink-3 hover:text-ink">
                <Icon name="close" size={16} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const push = useContext(ToastContext)
  if (!push) throw new Error('useToast must be used inside <ToastProvider>')
  return push
}
