import { createContext, useCallback, useContext, useMemo, useState } from 'react'

// Holds the latest citizen result in memory only. Nothing is written to
// localStorage, sessionStorage or IndexedDB (ADR-001): a refresh clears it.
//   kind: 'message' | 'url' | 'email' | 'qr' | 'identifier' | 'screenshot' | 'voice'

const ResultContext = createContext(null)

export function ResultProvider({ children }) {
  const [entry, setEntry] = useState(null)
  const save = useCallback((kind, input, result) => setEntry({ kind, input, result, at: new Date().toISOString() }), [])
  const clear = useCallback(() => setEntry(null), [])
  const value = useMemo(() => ({ entry, save, clear }), [entry, save, clear])
  return <ResultContext.Provider value={value}>{children}</ResultContext.Provider>
}

export function useResult() {
  const context = useContext(ResultContext)
  if (!context) throw new Error('useResult must be used inside <ResultProvider>')
  return context
}
