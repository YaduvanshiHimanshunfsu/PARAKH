import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Self-hosted fonts and icons: no Google Fonts or CDN requests, so the demo
// works offline and the CSP can stay `font-src 'self'` (H.0 step 4).
import '@fontsource-variable/plus-jakarta-sans'
import '@fontsource-variable/jetbrains-mono'
import '@fontsource/noto-sans-devanagari/400.css'
import '@fontsource/noto-sans-devanagari/600.css'
import '@fontsource/noto-sans-devanagari/700.css'
import 'material-symbols/outlined.css'
import './design/tokens.css'

import { I18nProvider } from './lib/i18n'
import { ToastProvider } from './design/ui'
import { AuthProvider } from './app/AuthContext'
import { ResultProvider } from './app/ResultContext'
import { createRouter } from './app/router'
import { ApiError } from './lib/api'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // Retry once on network trouble, never on 4xx (a bad request stays bad).
      retry: (count, error) => count < 1 && (!(error instanceof ApiError) || error.status === 0 || error.status >= 500),
    },
    mutations: { retry: false },
  },
})

const router = createRouter()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <ToastProvider>
          <AuthProvider>
            <ResultProvider>
              <RouterProvider router={router} />
            </ResultProvider>
          </AuthProvider>
        </ToastProvider>
      </I18nProvider>
    </QueryClientProvider>
  </StrictMode>,
)
