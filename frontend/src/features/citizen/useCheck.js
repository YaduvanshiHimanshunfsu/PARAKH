import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { citizenApi } from '../../lib/api'
import { useResult } from '../../app/ResultContext'

// One entry point for every citizen check. The result is kept in memory only
// (ResultContext) and shown on /result.

const RUNNERS = {
  message: ({ text, language }) => citizenApi.analyseMessage(text, language),
  screenshot: ({ text, language }) => citizenApi.analyseMessage(text, language),
  voice: ({ text, language }) => citizenApi.analyseMessage(text, language),
  url: ({ url }) => citizenApi.analyseUrl(url),
  email: ({ email }) => citizenApi.analyseEmail(email),
  qr: ({ payload }) => citizenApi.analyseQr(payload),
  identifier: ({ value }) => citizenApi.identifierCheck(value),
}

export function useCheck({ navigateOnSuccess = true } = {}) {
  const { save } = useResult()
  const navigate = useNavigate()
  return useMutation({
    mutationFn: async ({ kind, input }) => {
      const runner = RUNNERS[kind]
      if (!runner) throw new Error(`Unknown check: ${kind}`)
      return runner(input)
    },
    onSuccess: (result, { kind, input }) => {
      save(kind, input, result)
      if (navigateOnSuccess) navigate('/result')
    },
  })
}
