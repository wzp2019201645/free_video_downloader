/** Mirrors backend/services/entitlements.py format_requires_membership. */
const CAPPED_VIDEO = /^bestvideo\[height<=(\d+)\]\+bestaudio\/best$/

export function formatRequiresMembership(formatId) {
  if (formatId === 'bestaudio/best') return false
  const match = CAPPED_VIDEO.exec(formatId || '')
  if (match) return Number(match[1]) > 720
  return true
}

export function formatDate(unixSeconds) {
  if (!unixSeconds) return ''
  return new Date(unixSeconds * 1000).toLocaleDateString('zh-CN')
}
