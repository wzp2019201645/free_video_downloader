import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

export async function fetchVideoInfo(url) {
  const { data } = await api.post('/info', { url })
  return data
}

export async function startDownload(url, formatId) {
  const { data } = await api.post('/download', { url, format_id: formatId })
  return data
}

export async function getTaskStatus(taskId) {
  const { data } = await api.get(`/tasks/${taskId}`)
  return data
}

export function getDownloadUrl(taskId) {
  return `/api/files/${taskId}`
}

/** Use backend proxy so Bilibili etc. thumbnails load reliably */
export function getThumbnailUrl(thumbnail) {
  if (!thumbnail) return ''
  return `/api/thumbnail?url=${encodeURIComponent(thumbnail)}`
}

/**
 * Save file with native "Save As" dialog when supported (Chrome/Edge),
 * otherwise trigger browser download.
 */
export async function saveFileToDisk(taskId, filename) {
  const url = getDownloadUrl(taskId)
  const safeName = filename || 'video.mp4'

  if (window.showSaveFilePicker) {
    try {
      const ext = safeName.includes('.') ? safeName.split('.').pop() : 'mp4'
      // Must open picker during the click gesture, before any await fetch
      const handle = await window.showSaveFilePicker({
        suggestedName: safeName,
        types: [
          {
            description: 'Video file',
            accept: { 'application/octet-stream': [`.${ext}`], 'video/*': [`.${ext}`] },
          },
        ],
      })
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error('文件下载失败')
      }
      const blob = await response.blob()
      const writable = await handle.createWritable()
      await writable.write(blob)
      await writable.close()
      return
    } catch (err) {
      if (err.name === 'AbortError') return
      throw err
    }
  }

  const response = await fetch(url)
  if (!response.ok) {
    throw new Error('文件下载失败')
  }
  const blob = await response.blob()

  const blobUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = safeName
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(blobUrl)
}

export default api
