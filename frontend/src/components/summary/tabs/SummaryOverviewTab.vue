<template>
  <div class="space-y-5">
    <div class="flex flex-wrap gap-2">
      <span class="tag"># {{ getSubtitleSourceLabel(result.subtitle_source) }}</span>
      <span v-for="tag in result.tags" :key="tag" class="tag">{{ tag }}</span>
    </div>

    <div>
      <h4 class="text-sm font-semibold text-gray-700 mb-2">整体摘要</h4>
      <p class="text-sm text-gray-800 leading-relaxed">{{ result.overview }}</p>
    </div>

    <div v-if="result.key_points?.length">
      <h4 class="text-sm font-semibold text-gray-700 mb-2">核心要点</h4>
      <ul class="space-y-1.5">
        <li
          v-for="(point, i) in result.key_points"
          :key="i"
          class="text-sm text-gray-800 flex gap-2"
        >
          <span class="text-primary shrink-0">•</span>
          <span>{{ point }}</span>
        </li>
      </ul>
    </div>

    <div v-if="result.chapters?.length">
      <h4 class="text-sm font-semibold text-gray-700 mb-2">章节大纲</h4>
      <div class="space-y-3">
        <div
          v-for="(ch, i) in result.chapters"
          :key="i"
          class="p-3 rounded-xl bg-gray-50 border border-gray-100"
        >
          <div class="flex items-center gap-2 mb-1">
            <span class="text-xs font-mono text-primary bg-primary-light px-2 py-0.5 rounded">
              {{ formatTs(ch.start_seconds) }}
            </span>
            <span class="text-sm font-medium text-gray-900">{{ ch.title }}</span>
          </div>
          <p class="text-xs text-gray-600 leading-relaxed">{{ ch.summary }}</p>
        </div>
      </div>
    </div>

    <div class="flex flex-col sm:flex-row gap-3 pt-2">
      <button
        class="btn-primary flex-1 py-2.5 text-sm"
        :disabled="copying"
        @click="handleCopy"
      >
        {{ copied ? '已复制' : copying ? '复制中…' : '复制 Markdown' }}
      </button>
      <button
        class="px-6 py-2.5 rounded-full border border-gray-200 text-gray-700 text-sm
               hover:bg-gray-50 transition-colors flex-1"
        :disabled="saving"
        @click="handleSave"
      >
        {{ saving ? '保存中…' : '保存为 .md 文件' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  getSubtitleSourceLabel,
  copySummaryMarkdown,
  saveSummaryToDisk,
  formatTimestampForDisplay,
} from '../../../api/summaryClient'

const props = defineProps({
  result: { type: Object, required: true },
  title: { type: String, default: '' },
})

const emit = defineEmits(['error'])

const copying = ref(false)
const copied = ref(false)
const saving = ref(false)

function formatTs(seconds) {
  return formatTimestampForDisplay(seconds)
}

async function handleCopy() {
  if (copying.value) return
  copying.value = true
  try {
    await copySummaryMarkdown(props.result)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    emit('error', '复制失败，请手动选择复制')
  } finally {
    copying.value = false
  }
}

async function handleSave() {
  if (saving.value) return
  saving.value = true
  try {
    await saveSummaryToDisk(props.result, props.title)
  } catch (err) {
    if (err.name !== 'AbortError') {
      emit('error', err.message || '保存失败')
    }
  } finally {
    saving.value = false
  }
}
</script>
