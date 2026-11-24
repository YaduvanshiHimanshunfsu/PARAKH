import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { layoutGraph } from './campaigns/NetworkGraph'
import { trend } from './HeatlistPage'
import { timeAgo } from './shared'
import { StackedBars } from '../../design/ui/Charts'

const nodes = [
  { id: 'c1', kind: 'case' },
  { id: 'c2', kind: 'case' },
  { id: 'c3', kind: 'case' },
  { id: 'i1', kind: 'identifier' },
]
const edges = [
  { source: 'c1', target: 'i1', kind: 'identifier' },
  { source: 'c2', target: 'i1', kind: 'identifier' },
  { source: 'c3', target: 'i1', kind: 'identifier' },
  { source: 'c1', target: 'c2', kind: 'similar' },
  { source: 'c1', target: 'missing', kind: 'identifier' },
]

describe('campaign graph layout', () => {
  it('is deterministic for the same data', () => {
    const a = layoutGraph(nodes, edges).nodes.map((n) => [n.id, n.x.toFixed(3), n.y.toFixed(3)])
    const b = layoutGraph(nodes, edges).nodes.map((n) => [n.id, n.x.toFixed(3), n.y.toFixed(3)])
    expect(a).toEqual(b)
  })

  it('keeps every node inside the view box and drops dangling edges', () => {
    const { nodes: placed, edges: kept } = layoutGraph(nodes, edges, { width: 900, height: 560 })
    for (const node of placed) {
      expect(node.x).toBeGreaterThanOrEqual(0)
      expect(node.x).toBeLessThanOrEqual(900)
      expect(node.y).toBeGreaterThanOrEqual(0)
      expect(node.y).toBeLessThanOrEqual(560)
    }
    expect(kept).toHaveLength(4)
  })

  it('does not mutate the input', () => {
    layoutGraph(nodes, edges)
    expect(nodes[0]).toEqual({ id: 'c1', kind: 'case' })
    expect(edges[0].source).toBe('c1')
  })
})

describe('heat-list trend', () => {
  it('describes week-on-week change', () => {
    expect(trend(0, 0).label).toBe('Quiet')
    expect(trend(3, 0).label).toBe('New this week')
    expect(trend(6, 3).label).toBe('+100% vs last week')
    expect(trend(1, 4).label).toBe('-75% vs last week')
    expect(trend(2, 2).label).toBe('Same as last week')
  })
})

describe('timeAgo', () => {
  it('formats relative times and handles missing values', () => {
    const now = Date.parse('2026-11-24T12:00:00Z')
    expect(timeAgo('2026-11-24T11:58:00Z', now)).toMatch(/2 minutes ago/)
    expect(timeAgo('2026-11-21T12:00:00Z', now)).toMatch(/3 days ago/)
    expect(timeAgo(null)).toBe('—')
  })
})

describe('StackedBars', () => {
  const series = [
    { key: 'low', label: 'Low', color: '#059669' },
    { key: 'high', label: 'High', color: '#dc2626' },
  ]
  const data = [
    { date: '2026-11-23', low: 1, high: 2 },
    { date: '2026-11-24', low: 0, high: 4 },
  ]

  it('has a legend, an accessible label per day, and a table view with totals', () => {
    render(<StackedBars series={series} data={data} label="Cases per day" />)
    expect(screen.getByRole('img', { name: 'Cases per day' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Legend' })).toHaveTextContent('High')
    expect(screen.getByLabelText('2026-11-24: Low 0, High 4')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show table' }))
    const rows = screen.getAllByRole('row')
    expect(rows[1]).toHaveTextContent('2026-11-23')
    expect(rows[1]).toHaveTextContent('3')
    expect(rows[2]).toHaveTextContent('4')
  })

  it('shows a tooltip for the hovered day', () => {
    render(<StackedBars series={series} data={data} label="Cases per day" />)
    fireEvent.mouseEnter(screen.getByLabelText('2026-11-23: Low 1, High 2'))
    expect(screen.getByRole('tooltip')).toHaveTextContent(/Total\s*3/)
  })
})
