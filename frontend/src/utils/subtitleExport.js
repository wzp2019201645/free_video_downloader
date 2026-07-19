/** Build SRT / TXT subtitle files from transcript segments. */

function pad2(n) {
  return String(n).padStart(2, '0')
}

function pad3(n) {
  return String(n).padStart(3, '0')
}

/** Format seconds to SRT timestamp: HH:MM:SS,mmm */
export function formatSrtTimestamp(seconds) {
  const totalMs = Math.max(0, Math.round((seconds || 0) * 1000))
  const ms = totalMs % 1000
  const totalSec = Math.floor(totalMs / 1000)
  const s = totalSec % 60
  const totalMin = Math.floor(totalSec / 60)
  const m = totalMin % 60
  const h = Math.floor(totalMin / 60)
  return `${pad2(h)}:${pad2(m)}:${pad2(s)},${pad3(ms)}`
}

function formatTxtTimestamp(seconds) {
  const total = Math.floor(seconds || 0)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${pad2(m)}:${pad2(s)}`
}

export function buildSrtContent(transcript) {
  const segments = transcript || []
  return segments
    .map((seg, i) => {
      const start = formatSrtTimestamp(seg.start)
      const end = formatSrtTimestamp(seg.end ?? (seg.start + 2))
      const text = String(seg.text || '').trim()
      return `${i + 1}\n${start} --> ${end}\n${text}\n`
    })
    .join('\n')
}

export function buildTxtContent(transcript) {
  const segments = transcript || []
  return segments
    .map((seg) => `[${formatTxtTimestamp(seg.start)}] ${String(seg.text || '').trim()}`)
    .join('\n')
}
