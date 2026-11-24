import { describe, expect, it } from 'vitest'
import shared from '../../../tests/fixtures/identifier_vectors.json'
import { CLIENT_TYPES, detectIdentifiers, guessIdentifierType } from './identifiers'

// The same vectors pin the server extractor (tests/test_identifier_vectors.py).
describe('client identifier preview matches the server extractor', () => {
  it('covers the same identifier types as the vectors file', () => {
    expect(CLIENT_TYPES).toEqual(shared.client_types)
  })

  for (const vector of shared.vectors) {
    it(vector.name, () => {
      const found = detectIdentifiers(vector.text).map(({ type, value }) => ({ type, value }))
      expect(found).toEqual(vector.expected)
    })
  }
})

describe('guessIdentifierType', () => {
  it.each([
    ['richplan@ybl', 'UPI'],
    ['+91 98123 45670', 'PHONE'],
    ['sbi-verify-kyc.in', 'DOMAIN'],
    ['https://t.me/RichPlanOfficial', 'TELEGRAM'],
    ['45.133.1.9', 'IP'],
    ['SBIN0001428', 'IFSC'],
    ['PRK-20261118-K7P2QX', null],
    ['', null],
  ])('%s → %s', (input, expected) => {
    expect(guessIdentifierType(input)).toBe(expected)
  })
})
