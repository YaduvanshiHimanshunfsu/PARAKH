import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import en from '../content/en.json'
import hi from '../content/hi.json'

// Small dictionary i18n. Bilingual headings stay bilingual as designed; this
// switches body copy and controls. Missing Hindi keys fall back to English so a
// screen never shows a raw key.

const DICTIONARIES = { en, hi }
const STORAGE_KEY = 'parakh.lang'
const I18nContext = createContext(null)

function initialLanguage() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'en' || saved === 'hi') return saved
  } catch {
    /* storage unavailable */
  }
  return 'en'
}

export function translate(dictionaries, lang, key, vars) {
  const template = dictionaries[lang]?.[key] ?? dictionaries.en?.[key] ?? key
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (match, name) => (name in vars ? String(vars[name]) : match))
}

export function I18nProvider({ children, initial }) {
  const [lang, setLangState] = useState(initial || initialLanguage)

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  const setLang = useCallback((next) => {
    setLangState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      /* storage unavailable */
    }
  }, [])

  const value = useMemo(
    () => ({ lang, setLang, t: (key, vars) => translate(DICTIONARIES, lang, key, vars) }),
    [lang, setLang],
  )
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const context = useContext(I18nContext)
  if (!context) throw new Error('useI18n must be used inside <I18nProvider>')
  return context
}
