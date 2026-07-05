import axios from 'axios'

const summaryApi = axios.create({
  baseURL: '/api/summary',
  timeout: 300000,
})

export async function startSummary(url) {
  const { data } = await summaryApi.post('', { url })
  return data
}

export async function getSummaryStatus(taskId) {
  const { data } = await summaryApi.get(`/tasks/${taskId}`)
  return data
}

function formatTimestamp(seconds) {
  const total = Math.floor(seconds || 0)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

const SOURCE_LABELS = {
  bilibili_api: 'B站官方字幕',
  ytdlp: '平台字幕（yt-dlp）',
  whisper: '语音识别（Whisper）',
}

export function getSubtitleSourceLabel(source) {
  return SOURCE_LABELS[source] || source
}

export function buildSummaryMarkdown(result) {
  const lines = []
  lines.push(`# ${result.title}`)
  lines.push('')
  lines.push(
    `> 时长：${result.duration ? formatDuration(result.duration) : '未知'} | ` +
    `字幕来源：${getSubtitleSourceLabel(result.subtitle_source)} | 由 DeepSeek 生成`
  )
  lines.push('')
  lines.push('## 整体摘要')
  lines.push('')
  lines.push(result.overview || '')
  lines.push('')

  if (result.key_points?.length) {
    lines.push('## 核心要点')
    lines.push('')
    for (const point of result.key_points) {
      lines.push(`- ${point}`)
    }
    lines.push('')
  }

  if (result.chapters?.length) {
    lines.push('## 章节大纲')
    lines.push('')
    for (const ch of result.chapters) {
      lines.push(`### [${formatTimestamp(ch.start_seconds)}] ${ch.title}`)
      lines.push('')
      lines.push(ch.summary || '')
      lines.push('')
    }
  }

  if (result.tags?.length) {
    lines.push('## 标签')
    lines.push('')
    lines.push(result.tags.join(' '))
    lines.push('')
  }

  if (result.transcript?.length) {
    lines.push('## 全文转录')
    lines.push('')
    for (const seg of result.transcript) {
      lines.push(`[${formatTimestamp(seg.start)}] ${seg.text}`)
    }
  }

  return lines.join('\n')
}

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export async function saveSummaryToDisk(result, filename) {
  const markdown = buildSummaryMarkdown(result)
  const safeName = (filename || result.title || 'video-summary').replace(/[\\/:*?"<>|]/g, '_')
  const suggestedName = safeName.endsWith('.md') ? safeName : `${safeName}.md`

  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName,
        types: [
          {
            description: 'Markdown 文件',
            accept: { 'text/markdown': ['.md'] },
          },
        ],
      })
      const writable = await handle.createWritable()
      await writable.write(markdown)
      await writable.close()
      return
    } catch (err) {
      if (err.name === 'AbortError') return
      throw err
    }
  }

  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
  const blobUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = suggestedName
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(blobUrl)
}

export async function copySummaryMarkdown(result) {
  const markdown = buildSummaryMarkdown(result)
  await navigator.clipboard.writeText(markdown)
}

export function getStatusLabel(status) {
  const labels = {
    pending: '排队中…',
    extracting_subtitle: '正在获取字幕…',
    summarizing: 'AI 总结中…',
    completed: '总结完成',
    failed: '总结失败',
  }
  return labels[status] || status
}

export function formatTimestampForDisplay(seconds) {
  return formatTimestamp(seconds)
}
