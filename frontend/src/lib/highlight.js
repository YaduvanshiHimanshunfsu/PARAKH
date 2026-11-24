// Split text into plain and highlighted segments for the phrases the backend
// flagged (red_flags[].phrase). Matching is case-insensitive; overlapping
// matches are merged so the output is a clean, non-overlapping sequence.

export function highlightSegments(text = '', phrases = []) {
  const source = String(text)
  const lower = source.toLowerCase()
  const ranges = []
  for (const [index, raw] of phrases.entries()) {
    const phrase = String(raw || '').trim().toLowerCase()
    if (phrase.length < 2) continue
    let from = 0
    while (from <= lower.length) {
      const at = lower.indexOf(phrase, from)
      if (at === -1) break
      ranges.push({ start: at, end: at + phrase.length, flag: index })
      from = at + phrase.length
    }
  }
  ranges.sort((a, b) => a.start - b.start || b.end - a.end)

  const merged = []
  for (const range of ranges) {
    const last = merged[merged.length - 1]
    if (last && range.start < last.end) last.end = Math.max(last.end, range.end)
    else merged.push({ ...range })
  }

  const segments = []
  let cursor = 0
  for (const range of merged) {
    if (range.start > cursor) segments.push({ text: source.slice(cursor, range.start), flag: null })
    segments.push({ text: source.slice(range.start, range.end), flag: range.flag })
    cursor = range.end
  }
  if (cursor < source.length) segments.push({ text: source.slice(cursor), flag: null })
  return segments
}
