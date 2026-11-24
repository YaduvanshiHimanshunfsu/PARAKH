import { useMemo, useState } from 'react'
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY } from 'd3-force'
import { CHART_RISK } from '../../../design/ui'
import { identifierMeta } from '../../../design/vocab'

// Case ↔ identifier network for the campaign map. The layout is computed
// synchronously with a seeded random source, so the same data always gives
// the same picture (stable for screenshots and for officers comparing views).

const WIDTH = 900
const HEIGHT = 560

function lcg(seed) {
  let state = seed >>> 0
  return () => {
    state = (1664525 * state + 1013904223) >>> 0
    return state / 4294967296
  }
}

export function layoutGraph(nodes, edges, { width = WIDTH, height = HEIGHT, ticks = 300 } = {}) {
  const simNodes = nodes.map((node) => ({ ...node }))
  const ids = new Set(simNodes.map((node) => node.id))
  const simEdges = edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)).map((edge) => ({ ...edge }))
  const simulation = forceSimulation(simNodes)
    .randomSource(lcg(42))
    .force('link', forceLink(simEdges).id((node) => node.id).distance((edge) => (edge.kind === 'similar' ? 46 : 64)).strength(0.7))
    .force('charge', forceManyBody().strength(-170))
    .force('collide', forceCollide().radius((node) => (node.kind === 'case' ? 15 : 12)))
    .force('center', forceCenter(width / 2, height / 2))
    .force('x', forceX(width / 2).strength(0.04))
    .force('y', forceY(height / 2).strength(0.06))
    .stop()
  for (let i = 0; i < ticks; i += 1) simulation.tick()
  // Fit into the viewBox with a margin.
  const xs = simNodes.map((n) => n.x)
  const ys = simNodes.map((n) => n.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const scale = Math.min((width - 60) / Math.max(1, maxX - minX), (height - 60) / Math.max(1, maxY - minY), 3)
  simNodes.forEach((node) => {
    node.x = 30 + (node.x - minX) * scale + (width - 60 - (maxX - minX) * scale) / 2
    node.y = 30 + (node.y - minY) * scale + (height - 60 - (maxY - minY) * scale) / 2
  })
  return { nodes: simNodes, edges: simEdges }
}

export function NetworkGraph({ nodes, edges, onSelect, label }) {
  const layout = useMemo(() => layoutGraph(nodes, edges), [nodes, edges])
  const [hover, setHover] = useState(null)
  const neighbours = useMemo(() => {
    if (!hover) return null
    const set = new Set([hover])
    layout.edges.forEach((edge) => {
      if (edge.source.id === hover) set.add(edge.target.id)
      if (edge.target.id === hover) set.add(edge.source.id)
    })
    return set
  }, [hover, layout])
  const hovered = hover ? layout.nodes.find((node) => node.id === hover) : null

  return (
    <div className="relative">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-auto w-full rounded-card bg-canvas" role="img" aria-label={label}>
        {layout.edges.map((edge, index) => {
          const active = !neighbours || (neighbours.has(edge.source.id) && neighbours.has(edge.target.id))
          return (
            <line
              key={index}
              x1={edge.source.x}
              y1={edge.source.y}
              x2={edge.target.x}
              y2={edge.target.y}
              stroke={edge.kind === 'similar' ? '#7c3aed' : '#94a3b8'}
              strokeWidth={edge.kind === 'similar' ? 2 : 1.4}
              strokeDasharray={edge.kind === 'similar' ? '4 3' : undefined}
              opacity={active ? 0.85 : 0.12}
            />
          )
        })}
        {layout.nodes.map((node) => {
          const dim = neighbours && !neighbours.has(node.id)
          const common = {
            key: node.id,
            opacity: dim ? 0.2 : 1,
            style: { cursor: 'pointer' },
            tabIndex: 0,
            role: 'button',
            'aria-label': node.kind === 'case' ? `Case ${node.case_id}, ${node.risk_level} risk` : `${identifierMeta(node.identifier_type).label} ${node.value}, in ${node.case_count} cases`,
            onMouseEnter: () => setHover(node.id),
            onMouseLeave: () => setHover(null),
            onFocus: () => setHover(node.id),
            onBlur: () => setHover(null),
            onClick: () => onSelect?.(node),
            onKeyDown: (event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                onSelect?.(node)
              }
            },
          }
          if (node.kind === 'case') {
            return (
              <g {...common}>
                <circle cx={node.x} cy={node.y} r={10} fill={CHART_RISK[node.risk_level] || '#64748b'} stroke="#ffffff" strokeWidth="2" />
              </g>
            )
          }
          const color = identifierMeta(node.identifier_type).color
          return (
            <g {...common}>
              <rect x={node.x - 8} y={node.y - 8} width={16} height={16} rx={4} fill="#ffffff" stroke={color} strokeWidth="2.5" />
            </g>
          )
        })}
      </svg>
      {hovered && (
        <div
          role="tooltip"
          className="pointer-events-none absolute z-10 max-w-[260px] -translate-x-1/2 rounded-chip border border-line bg-card px-3 py-2 text-body-sm shadow-l3"
          style={{ left: `${(hovered.x / WIDTH) * 100}%`, top: `calc(${(hovered.y / HEIGHT) * 100}% + 16px)` }}
        >
          {hovered.kind === 'case' ? (
            <>
              <p className="font-mono font-semibold text-ink">{hovered.case_id}</p>
              <p className="text-ink-2">{hovered.label}</p>
            </>
          ) : (
            <>
              <p className="text-label-ui uppercase text-ink-3">{identifierMeta(hovered.identifier_type).label}</p>
              <p className="break-all font-mono font-semibold text-ink">{hovered.value}</p>
              <p className="text-ink-2">In {hovered.case_count} cases</p>
            </>
          )}
        </div>
      )}
      <ul className="mt-3 flex flex-wrap gap-4 text-body-sm text-ink-2" aria-label="Legend">
        <li className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full" style={{ background: CHART_RISK.HIGH }} /> High-risk case</li>
        <li className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full" style={{ background: CHART_RISK.MEDIUM }} /> Medium-risk case</li>
        <li className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full" style={{ background: CHART_RISK.LOW }} /> Low-risk case</li>
        <li className="flex items-center gap-1.5"><span className="h-3 w-3 rounded border-2 border-ink-3 bg-white" /> Shared identifier (border = type)</li>
        <li className="flex items-center gap-1.5"><span className="w-5 border-t-2 border-dashed border-[#7c3aed]" /> Same / near-same text</li>
      </ul>
    </div>
  )
}
