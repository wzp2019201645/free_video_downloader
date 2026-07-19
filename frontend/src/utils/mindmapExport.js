/**
 * Reliable markmap export.
 * Markmap renders labels in <foreignObject>; html-to-image / raw SVG clone
 * often fail silently. We convert to pure SVG <text> for export, then:
 * - SVG: serialize + save
 * - PNG: draw SVG onto canvas at pixelRatio scale
 *
 * Download uses showSaveFilePicker first (keeps user gesture), with <a download> fallback.
 */

import { downloadBlob, safeFilename } from './downloadBlob'

function foreignObjectText(fo) {
  const el = fo.querySelector('div, span, p') || fo
  return (el.textContent || '').replace(/\s+/g, ' ').trim()
}

/**
 * Build a self-contained, foreignObject-free SVG string from a rendered markmap SVG.
 */
export function buildExportableSvgString(svgEl) {
  if (!svgEl) throw new Error('思维导图尚未渲染')

  const clone = svgEl.cloneNode(true)
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  clone.querySelectorAll('foreignObject').forEach((fo) => {
    const text = foreignObjectText(fo)
    const x = Number.parseFloat(fo.getAttribute('x') || '0')
    const y = Number.parseFloat(fo.getAttribute('y') || '0')
    const width = Number.parseFloat(fo.getAttribute('width') || '0')
    const height = Number.parseFloat(fo.getAttribute('height') || '0')
    const textEl = document.createElementNS('http://www.w3.org/2000/svg', 'text')
    textEl.setAttribute('x', String(x + Math.max(width, 0) / 2))
    textEl.setAttribute('y', String(y + Math.max(height, 0) / 2))
    textEl.setAttribute('text-anchor', 'middle')
    textEl.setAttribute('dominant-baseline', 'middle')
    textEl.setAttribute('font-size', '14')
    textEl.setAttribute('font-family', 'system-ui, -apple-system, "Segoe UI", sans-serif')
    textEl.setAttribute('fill', '#111827')
    textEl.textContent = text
    fo.replaceWith(textEl)
  })

  // Measure from live SVG for accurate viewBox (clone may lack layout)
  let bbox
  try {
    bbox = svgEl.getBBox()
  } catch {
    bbox = {
      x: 0,
      y: 0,
      width: svgEl.clientWidth || 960,
      height: svgEl.clientHeight || 640,
    }
  }
  const pad = 24
  const width = Math.max(Math.ceil(bbox.width + pad * 2), 120)
  const height = Math.max(Math.ceil(bbox.height + pad * 2), 120)
  const vbX = bbox.x - pad
  const vbY = bbox.y - pad

  clone.setAttribute('width', String(width))
  clone.setAttribute('height', String(height))
  clone.setAttribute('viewBox', `${vbX} ${vbY} ${width} ${height}`)
  clone.style.background = '#ffffff'

  const style = document.createElementNS('http://www.w3.org/2000/svg', 'style')
  style.textContent = `
    text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
    path { fill: none; }
  `
  clone.insertBefore(style, clone.firstChild)

  // White background rect behind content
  const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
  bg.setAttribute('x', String(vbX))
  bg.setAttribute('y', String(vbY))
  bg.setAttribute('width', String(width))
  bg.setAttribute('height', String(height))
  bg.setAttribute('fill', '#ffffff')
  clone.insertBefore(bg, style.nextSibling)

  const serialized = new XMLSerializer().serializeToString(clone)
  if (!serialized || serialized.length < 50) {
    throw new Error('导出 SVG 内容为空')
  }
  // Ensure XML declaration-free but valid SVG root for Image()
  return serialized.includes('xmlns=')
    ? serialized
    : serialized.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')
}

export async function svgStringToPngBlob(svgString, pixelRatio = 3) {
  const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(svgBlob)

  try {
    const img = await loadImage(url)
    const width = Math.max(1, img.naturalWidth || img.width)
    const height = Math.max(1, img.naturalHeight || img.height)
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(width * pixelRatio)
    canvas.height = Math.round(height * pixelRatio)
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('无法创建画布')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
    ctx.drawImage(img, 0, 0, width, height)

    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob(
        (b) => (b ? resolve(b) : reject(new Error('PNG 编码失败'))),
        'image/png',
      )
    })
    return blob
  } finally {
    URL.revokeObjectURL(url)
  }
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('SVG 转图片失败'))
    img.src = url
  })
}

/**
 * Open save dialog first (preserves user gesture), then write blob.
 * Falls back to anchor download when File System Access API is unavailable.
 */
export async function saveBlobAsFile({
  buildBlob,
  filename,
  mimeType,
  description,
  extension,
}) {
  const suggestedName = safeFilename(filename, extension)
  let writable = null

  if (typeof window.showSaveFilePicker === 'function') {
    try {
      const accept = { [mimeType]: [extension.startsWith('.') ? extension : `.${extension}`] }
      const handle = await window.showSaveFilePicker({
        suggestedName,
        types: [{ description: description || '文件', accept }],
      })
      writable = await handle.createWritable()
    } catch (err) {
      if (err?.name === 'AbortError') {
        return { cancelled: true }
      }
      // Fall through to anchor download
      writable = null
    }
  }

  const blob = await buildBlob()
  if (!(blob instanceof Blob) || blob.size === 0) {
    throw new Error('导出文件为空')
  }

  if (writable) {
    try {
      await writable.write(blob)
      await writable.close()
      return { cancelled: false, method: 'picker' }
    } catch (err) {
      try { await writable.abort?.() } catch { /* ignore */ }
      throw err
    }
  }

  downloadBlob(blob, suggestedName)
  return { cancelled: false, method: 'anchor' }
}

export function svgStringToBlob(svgString) {
  // Prepend XML header helps some Windows apps open the file
  const content = svgString.startsWith('<?xml')
    ? svgString
    : `<?xml version="1.0" encoding="UTF-8"?>\n${svgString}`
  return new Blob([content], { type: 'image/svg+xml;charset=utf-8' })
}
