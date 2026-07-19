/** Trigger a browser file download from a Blob or data URL. */

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  // Delay revoke so the browser can start the download
  setTimeout(() => {
    if (a.parentNode) document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, 2000)
}

export function downloadDataUrl(dataUrl, filename) {
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = filename
  a.rel = 'noopener'
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  setTimeout(() => {
    if (a.parentNode) document.body.removeChild(a)
  }, 2000)
}

export function safeFilename(name, ext) {
  const base = (name || 'download').replace(/[\\/:*?"<>|]/g, '_').trim() || 'download'
  if (!ext) return base
  const suffix = ext.startsWith('.') ? ext : `.${ext}`
  return base.toLowerCase().endsWith(suffix.toLowerCase()) ? base : `${base}${suffix}`
}
