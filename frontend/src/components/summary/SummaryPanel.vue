<template>
  <section class="px-4 pb-8">
    <div class="max-w-3xl mx-auto">
      <div class="card p-5 sm:p-6">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
          <div>
            <h3 class="text-base font-bold text-gray-900">AI 视频总结</h3>
            <p class="text-xs text-gray-500 mt-1">快速了解视频大纲与核心要点（DeepSeek）</p>
          </div>
          <button
            class="btn-primary px-6 py-2.5 text-sm shrink-0"
            :disabled="summarizing || !url"
            @click="handleSummary"
          >
            <span v-if="summarizing">{{ statusLabel }} {{ progress.toFixed(0) }}%</span>
            <span v-else-if="completed">重新总结</span>
            <span v-else>开始 AI 总结</span>
          </button>
        </div>

        <!-- 进度 -->
        <div
          v-if="summarizing"
          class="mb-4 p-4 rounded-xl bg-gray-50 border border-gray-100"
        >
          <div class="flex justify-between text-xs text-gray-500 mb-1.5">
            <span>{{ statusLabel }}</span>
            <span>{{ progress.toFixed(0) }}%</span>
          </div>
          <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              class="h-full bg-primary rounded-full transition-all duration-300"
              :style="{ width: progress + '%' }"
            />
          </div>
        </div>

        <!-- 错误 -->
        <div v-if="error" class="mb-4 p-4 rounded-xl bg-red-50 border border-red-100">
          <p class="text-sm text-red-600">{{ error }}</p>
        </div>

        <!-- 结果 -->
        <div v-if="result" class="space-y-5">
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

          <details v-if="result.transcript?.length" class="group">
            <summary class="text-sm font-semibold text-gray-700 cursor-pointer select-none">
              全文转录（{{ result.transcript.length }} 段）
            </summary>
            <div class="mt-3 max-h-64 overflow-y-auto space-y-1 p-3 rounded-xl bg-gray-50 border border-gray-100">
              <p
                v-for="(seg, i) in result.transcript"
                :key="i"
                class="text-xs text-gray-600"
              >
                <span class="font-mono text-gray-400 mr-2">{{ formatTs(seg.start) }}</span>
                {{ seg.text }}
              </p>
            </div>
          </details>

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
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import {
  startSummary,
  getSummaryStatus,
  getStatusLabel,
  getSubtitleSourceLabel,
  copySummaryMarkdown,
  saveSummaryToDisk,
  formatTimestampForDisplay,
} from '../../api/summaryClient'

const props = defineProps({
  url: { type: String, required: true },
  title: { type: String, default: '' },
})

const summarizing = ref(false)
const completed = ref(false)
const progress = ref(0)
const taskStatus = ref('')
const statusDetail = ref('')
const error = ref('')
const result = ref(null)
const copying = ref(false)
const copied = ref(false)
const saving = ref(false)
let pollTimer = null

const statusLabel = computed(() => {
  if (statusDetail.value) return statusDetail.value
  return getStatusLabel(taskStatus.value)
})

watch(() => props.url, () => {
  resetState()
})

function resetState() {
  if (pollTimer) clearInterval(pollTimer)
  summarizing.value = false
  completed.value = false
  progress.value = 0
  taskStatus.value = ''
  statusDetail.value = ''
  error.value = ''
  result.value = null
  copied.value = false
}

function formatTs(seconds) {
  return formatTimestampForDisplay(seconds)
}

async function pollTask(taskId) {
  try {
    const task = await getSummaryStatus(taskId)
    progress.value = task.progress || 0
    taskStatus.value = task.status
    statusDetail.value = task.status_detail || ''

    if (task.status === 'completed') {
      result.value = task.result
      summarizing.value = false
      completed.value = true
      return true
    }
    if (task.status === 'failed') {
      summarizing.value = false
      error.value = task.error || '总结失败'
      return true
    }
    return false
  } catch {
    summarizing.value = false
    error.value = '查询总结进度失败'
    return true
  }
}

async function handleSummary() {
  if (!props.url || summarizing.value) return
  resetState()
  summarizing.value = true
  error.value = ''

  try {
    const { task_id } = await startSummary(props.url)
    pollTimer = setInterval(async () => {
      const done = await pollTask(task_id)
      if (done) clearInterval(pollTimer)
    }, 1500)
    await pollTask(task_id)
  } catch (err) {
    summarizing.value = false
    error.value = err.response?.data?.detail || '创建总结任务失败'
  }
}

async function handleCopy() {
  if (!result.value || copying.value) return
  copying.value = true
  try {
    await copySummaryMarkdown(result.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    error.value = '复制失败，请手动选择复制'
  } finally {
    copying.value = false
  }
}

async function handleSave() {
  if (!result.value || saving.value) return
  saving.value = true
  try {
    await saveSummaryToDisk(result.value, props.title)
  } catch (err) {
    if (err.name !== 'AbortError') {
      error.value = err.message || '保存失败'
    }
  } finally {
    saving.value = false
  }
}
</script>
