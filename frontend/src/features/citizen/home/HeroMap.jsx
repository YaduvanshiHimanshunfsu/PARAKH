import { useEffect, useMemo, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { geoMercator, geoPath } from 'd3-geo'
import { feature } from 'topojson-client'
import { Icon } from '../../../design/ui'

// Hero map per the Stitch storyboard (design/stitch/parakh_hero_map_animation_
// storyboard_4_frame_sequence): 4 frames over 3.2 s with cubic-bezier(0.16, 1,
// 0.3, 1), then a slow ambient loop. Boundaries are Survey of India–derived
// (src/geo/SOURCES.md). Arcs, pulses and cards are illustrative, not live data,
// and are labelled as such.

const EASE = [0.16, 1, 0.3, 1]
const WIDTH = 560
const HEIGHT = 620

// Rajasthan division headquarters (longitude, latitude).
const HQ = [
  { name: 'Jaipur', hi: 'जयपुर', at: [75.7873, 26.9124], capital: true },
  { name: 'Jodhpur', hi: 'जोधपुर', at: [73.0243, 26.2389] },
  { name: 'Udaipur', hi: 'उदयपुर', at: [73.7125, 24.5854] },
  { name: 'Kota', hi: 'कोटा', at: [75.8648, 25.2138] },
  { name: 'Ajmer', hi: 'अजमेर', at: [74.6399, 26.4499] },
  { name: 'Bikaner', hi: 'बीकानेर', at: [73.3119, 28.0229] },
  { name: 'Bharatpur', hi: 'भरतपुर', at: [77.4895, 27.2152] },
]

// Illustrative origins of suspicious messages flowing to the citizen check.
const ORIGINS = [
  [77.209, 28.6139],
  [72.8777, 19.076],
  [88.3639, 22.5726],
  [77.5946, 12.9716],
  [78.4867, 17.385],
  [80.9462, 26.8467],
]

function useGeometry() {
  const [geo, setGeo] = useState(null)
  useEffect(() => {
    let alive = true
    import('../../../geo/india.topo.json').then((module) => {
      if (!alive) return
      const topo = module.default
      const india = feature(topo, topo.objects.india)
      const states = feature(topo, topo.objects.states)
      const projection = geoMercator().fitExtent(
        [
          [12, 12],
          [WIDTH - 12, HEIGHT - 12],
        ],
        india,
      )
      const path = geoPath(projection)
      const rajasthan = states.features.find((f) => f.properties.name === 'Rajasthan')
      setGeo({
        india: path(india),
        states: states.features.filter((f) => f !== rajasthan).map((f) => path(f)),
        rajasthan: path(rajasthan),
        hq: HQ.map((city) => ({ ...city, xy: projection(city.at) })),
        origins: ORIGINS.map((point) => projection(point)),
      })
    })
    return () => {
      alive = false
    }
  }, [])
  return geo
}

function arcPath([x1, y1], [x2, y2]) {
  const mx = (x1 + x2) / 2
  const my = (y1 + y2) / 2 - Math.hypot(x2 - x1, y2 - y1) * 0.25
  return `M${x1.toFixed(1)},${y1.toFixed(1)} Q${mx.toFixed(1)},${my.toFixed(1)} ${x2.toFixed(1)},${y2.toFixed(1)}`
}

export function HeroMap() {
  const geo = useGeometry()
  const reduce = useReducedMotion()
  const jaipur = geo?.hq[0].xy
  const arcs = useMemo(() => (geo ? geo.origins.map((origin) => arcPath(origin, jaipur)) : []), [geo, jaipur])

  // Frame timing (seconds); collapsed to 0 when motion is reduced.
  const t = (seconds) => (reduce ? 0 : seconds)
  const d = (seconds) => (reduce ? 0 : seconds)

  return (
    <div className="relative mx-auto aspect-[56/62] w-full max-w-[560px]">
      {!geo ? (
        <div className="absolute inset-0 animate-pulse rounded-hero bg-surface-container-low" aria-hidden="true" />
      ) : (
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-full w-full overflow-visible"
          role="img"
          aria-label="Map of India with Rajasthan highlighted. Illustration of suspicious messages being checked."
        >
          <defs>
            <linearGradient id="raj-fill" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#fbd5b5" />
              <stop offset="100%" stopColor="#f2a86b" />
            </linearGradient>
            <filter id="raj-lift" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="10" stdDeviation="9" floodColor="#c2410c" floodOpacity="0.28" />
            </filter>
            <radialGradient id="sweep" cx="0.5" cy="0.5" r="0.5">
              <stop offset="0%" stopColor="#1d4ed8" stopOpacity="0.16" />
              <stop offset="100%" stopColor="#1d4ed8" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Frame 1 — national baseline */}
          <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: d(0.8), ease: EASE }}>
            <path d={geo.india} fill="#eef1f6" stroke="#c7d0dd" strokeWidth="1" />
            {geo.states.map((pathData, index) => (
              <path key={index} d={pathData} fill="none" stroke="#dde3ec" strokeWidth="0.7" />
            ))}
          </motion.g>

          {/* Frame 2 — Rajasthan rises */}
          <motion.path
            d={geo.rajasthan}
            fill="url(#raj-fill)"
            stroke="#c2410c"
            strokeWidth="1.4"
            filter="url(#raj-lift)"
            initial={{ opacity: 0, y: 0 }}
            animate={{ opacity: 1, y: -8 }}
            transition={{ delay: t(0.8), duration: d(0.8), ease: EASE }}
          />

          {/* Frame 3 — telemetry pulse: arcs flow to Jaipur, HQ nodes pulse */}
          <g transform="translate(0,-8)">
            {arcs.map((pathData, index) => (
              <motion.path
                key={index}
                d={pathData}
                fill="none"
                stroke="#1d4ed8"
                strokeWidth="1.4"
                strokeLinecap="round"
                strokeDasharray="4 7"
                initial={{ opacity: 0, strokeDashoffset: 0 }}
                animate={reduce ? { opacity: 0.45 } : { opacity: [0, 0.55, 0.55], strokeDashoffset: [0, -110] }}
                transition={
                  reduce
                    ? { duration: 0 }
                    : { delay: 1.6 + index * 0.08, duration: 9, ease: 'linear', repeat: Infinity, times: [0, 0.05, 1] }
                }
              />
            ))}
            {!reduce && (
              <motion.circle
                cx={jaipur[0]}
                cy={jaipur[1]}
                r="90"
                fill="url(#sweep)"
                initial={{ scale: 0.2, opacity: 0 }}
                animate={{ scale: [0.2, 1.2], opacity: [0.9, 0] }}
                transition={{ delay: 1.6, duration: 3.2, repeat: Infinity, ease: 'easeOut' }}
              />
            )}
            {geo.hq.map((city, index) => (
              <g key={city.name}>
                {!reduce && (
                  <motion.circle
                    cx={city.xy[0]}
                    cy={city.xy[1]}
                    r={city.capital ? 7 : 5}
                    fill="none"
                    stroke={city.capital ? '#1d4ed8' : '#c2410c'}
                    strokeWidth="1.5"
                    initial={{ scale: 1, opacity: 0 }}
                    animate={{ scale: [1, 3], opacity: [0.8, 0] }}
                    transition={{ delay: 1.6 + index * 0.12, duration: 2.4, repeat: Infinity, ease: 'easeOut' }}
                    style={{ transformOrigin: `${city.xy[0]}px ${city.xy[1]}px` }}
                  />
                )}
                <motion.circle
                  cx={city.xy[0]}
                  cy={city.xy[1]}
                  r={city.capital ? 5 : 3.5}
                  fill={city.capital ? '#1d4ed8' : '#ffffff'}
                  stroke={city.capital ? '#ffffff' : '#c2410c'}
                  strokeWidth="1.6"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: t(1.6 + index * 0.06), duration: d(0.3) }}
                />
                {city.capital && (
                  <motion.text
                    x={city.xy[0] + 9}
                    y={city.xy[1] + 4}
                    fontSize="12"
                    fontWeight="700"
                    fill="#1e3a8a"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: t(1.9), duration: d(0.4) }}
                  >
                    Jaipur
                  </motion.text>
                )}
              </g>
            ))}
          </g>
        </svg>
      )}

      {/* Frame 4 — illustrative verdict cards */}
      {geo && (
        <>
          <motion.div
            className="glass absolute left-0 top-[16%] hidden max-w-[210px] rounded-chip px-3 py-2 text-body-sm shadow-l2 sm:block"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: t(2.4), duration: d(0.6), ease: EASE }}
          >
            <p className="flex items-center gap-1 text-label-ui uppercase text-risk-high-ink">
              <Icon name="sms" size={16} /> SMS · High risk
            </p>
            <p className="mt-0.5 text-ink-2">“Bijli bill unpaid — power cut tonight”</p>
          </motion.div>
          <motion.div
            className="glass absolute bottom-[12%] right-0 hidden max-w-[220px] rounded-chip px-3 py-2 text-body-sm shadow-l2 sm:block"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: t(2.7), duration: d(0.6), ease: EASE }}
          >
            <p className="flex items-center gap-1 text-label-ui uppercase text-risk-high-ink">
              <Icon name="android" size={16} /> APK · Do not install
            </p>
            <p className="mt-0.5 text-ink-2">RTO_Challan.apk reads your OTPs</p>
          </motion.div>
          <p className="absolute bottom-0 left-0 text-[11px] text-ink-3">Illustration · Boundaries: Survey of India via DataMeet</p>
        </>
      )}
    </div>
  )
}
