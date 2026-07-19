<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
      <p class="text-xs text-gray-500">共 {{ result.transcript?.length || 0 }} 段</p>
      <div class="flex flex-wrap items-center gap-3">
        <button
          type="button"
          class="text-xs text-primary hover:underline disabled:opacity-50"
          :disabled="!hasTranscript || downloading"
          @click="downloadSrt"
        >
          下载 SRT
        </button>
        <button
          type="button"
          class="text-xs text-primary hover:underline disabled:opacity-50"
          :disabled="!hasTranscript || downloading"
          @click="downloadTxt"
        >
          下载 TXT
        </button>
        <button
          type="button"
          class="text-xs text-primary hover:underline disabled:opacity-50"
          :disabled="!hasTranscript || copying"
          @click="handleCopyTranscript"
        >
          {{ copied ? '已复制' : '复制全文' }}
        </button>
      </div>
    </div>
    <div class="max-h-[28rem] overflow-y-auto space-y-1.5 p-4 rounded-xl bg-gray-50 border border-gray-100">
      <p
        v-for="(seg, i) in result.transcript"
        :key="i"
        class="text-sm text-gray-700 leading-relaxed"
      >
        <span class="font-mono text-xs text-gray-400 mr-2 shrink-0">{{ formatTs(seg.start) }}</span>
        {{ seg.text }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { formatTimestampForDisplay } from '../../../api/summaryClient'
import { downloadBlob, safeFilename } from '../../../utils/downloadBlob'
import { buildSrtContent, buildTxtContent } from '../../../utils/subtitleExport'

const props = defineProps({
  result: { type: Object, required: true },
})

const emit = defineEmits(['error'])

const copying = ref(false)
const copied = ref(false)
const downloading = ref(false)

const hasTranscript = computed(() => (props.result.transcript?.length || 0) > 0)

function formatTs(seconds) {
  return formatTimestampForDisplay(seconds)
}

function fileBase() {
  return safeFilename(props.result.title || 'subtitle', '')
}

async function handleCopyTranscript() {
  if (!hasTranscript.value || copying.value) return
  copying.value = true
  try {
    const text = props.result.transcript
      .map((seg) => `[${formatTs(seg.start)}] ${seg.text}`)
      .join('\n')
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    emit('error', '复制字幕失败')
  } finally {
    copying.value = false
  }
}

function downloadSrt() {
  if (!hasTranscript.value || downloading.value) return
  downloading.value = true
  try {
    const content = buildSrtContent(props.result.transcript)
    const blob = new Blob([content], { type: 'application/x-subrip;charset=utf-8' })
    downloadBlob(blob, safeFilename(fileBase(), '.srt'))
  } catch {
    emit('error', '下载 SRT 失败')
  } finally {
    downloading.value = false
  }
}

function downloadTxt() {
  if (!hasTranscript.value || downloading.value) return
  downloading.value = true
  try {
    const content = buildTxtContent(props.result.transcript)
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    downloadBlob(blob, safeFilename(fileBase(), '.txt'))
  } catch {
    emit('error', '下载 TXT 失败')
  } finally {
    downloading.value = false
  }
}
</script>
