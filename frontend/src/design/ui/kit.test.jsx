import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '../../lib/i18n'
import { ApiError } from '../../lib/api'
import { IdentifierChip, RiskBadge, RiskGauge, Segmented, StateBlock, ConsentCheckbox } from './index'

const wrap = (ui) => render(<I18nProvider initial="en"><MemoryRouter>{ui}</MemoryRouter></I18nProvider>)

describe('RiskBadge', () => {
  it('always shows text, never colour alone', () => {
    wrap(<RiskBadge level="SCAM" score={92} />)
    expect(screen.getByText(/High risk/)).toBeInTheDocument()
    expect(screen.getByText(/92/)).toBeInTheDocument()
  })
})

describe('RiskGauge', () => {
  it('exposes the value to screen readers and clamps it', () => {
    wrap(<RiskGauge value={140} level="HIGH" />)
    expect(screen.getByRole('img', { name: 'High risk: 100 out of 100' })).toBeInTheDocument()
  })
})

describe('IdentifierChip', () => {
  it('shows the type label and value, with an accessible copy button', async () => {
    const writeText = vi.fn(async () => {})
    Object.assign(navigator, { clipboard: { writeText } })
    wrap(<IdentifierChip type="UPI" value="richplan@ybl" count={5} />)
    expect(screen.getByText('richplan@ybl')).toBeInTheDocument()
    expect(screen.getByText('×5')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Copy UPI richplan@ybl' }))
    expect(writeText).toHaveBeenCalledWith('richplan@ybl')
  })
})

describe('Segmented', () => {
  it('is a radio group that reports the chosen value', async () => {
    const onChange = vi.fn()
    wrap(
      <Segmented
        label="Mode"
        value="message"
        onChange={onChange}
        options={[
          { value: 'message', label: 'Message' },
          { value: 'link', label: 'Link' },
        ]}
      />,
    )
    expect(screen.getByRole('radio', { name: 'Message' })).toBeChecked()
    await userEvent.click(screen.getByRole('radio', { name: 'Link' }))
    expect(onChange).toHaveBeenCalledWith('link')
  })
})

describe('ConsentCheckbox', () => {
  it('starts unchecked (ADR-001)', () => {
    wrap(<ConsentCheckbox checked={false} onChange={() => {}}>I agree</ConsentCheckbox>)
    expect(screen.getByRole('checkbox', { name: 'I agree' })).not.toBeChecked()
  })
})

describe('StateBlock', () => {
  const ok = (data) => <p>{data.length} rows</p>
  it('shows loading', () => {
    wrap(<StateBlock query={{ isPending: true }}>{ok}</StateBlock>)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
  it('shows an offline error with retry', async () => {
    const refetch = vi.fn()
    wrap(<StateBlock query={{ isPending: false, isError: true, error: new ApiError(0, 'down'), refetch }}>{ok}</StateBlock>)
    expect(screen.getByRole('alert')).toHaveTextContent('The PARAKH server could not be reached')
    await userEvent.click(screen.getByRole('button', { name: /Try again/ }))
    expect(refetch).toHaveBeenCalled()
  })
  it('shows empty, then data', () => {
    const { rerender } = wrap(<StateBlock query={{ data: [] }} isEmpty={(d) => !d.length}>{ok}</StateBlock>)
    expect(screen.getByText('Nothing to show yet')).toBeInTheDocument()
    rerender(<I18nProvider initial="en"><MemoryRouter><StateBlock query={{ data: [1, 2] }} isEmpty={(d) => !d.length}>{ok}</StateBlock></MemoryRouter></I18nProvider>)
    expect(screen.getByText('2 rows')).toBeInTheDocument()
  })
})
