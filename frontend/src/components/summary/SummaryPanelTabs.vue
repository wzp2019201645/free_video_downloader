<template>
  <section class="px-4 pb-8">
    <div class="max-w-3xl mx-auto">
      <div class="card p-5 sm:p-6">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
          <div>
            <h3 class="text-base font-bold text-gray-900">AI 视频总结</h3>
            <p class="text-xs text-gray-500 mt-1">总结摘要 · 字幕文本 · 思维导图 · AI 问答</p>
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

        <div v-if="error" class="mb-4 p-4 rounded-xl bg-red-50 border border-red-100">
          <p class="text-sm text-red-600">{{ error }}</p>
        </div>

        <div v-if="result">
          <div class="flex flex-wrap gap-1 p-1 mb-5 rounded-xl bg-gray-100">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              type="button"
              class="flex-1 min-w-[5rem] px-3 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors"
              :class="activeTab === tab.id
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'"
              @click="activeTab = tab.id"
            >
              {{ tab.label }}
            </button>
          </div>

          <SummaryOverviewTab
            v-show="activeTab === 'overview'"
            :result="result"
            :title="title"
            @error="error = $event"
          />

          <TranscriptTab
            v-show="activeTab === 'transcript'"
            :result="result"
            @error="error = $event"
          />

          <MindMapTab
            v-show="activeTab === 'mindmap'"
            :task-id="taskId"
            :active="activeTab === 'mindmap'"
            :title="result?.title || title"
          />

          <ChatTab
            v-show="activeTab === 'chat'"
            :task-id="taskId"
          />
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
} from '../../api/summaryClient'
import SummaryOverviewTab from './tabs/SummaryOverviewTab.vue'
import TranscriptTab from './tabs/TranscriptTab.vue'
import MindMapTab from './tabs/MindMapTab.vue'
import ChatTab from './tabs/ChatTab.vue'

const props = defineProps({
  url: { type: String, required: true },
  title: { type: String, default: '' },
})

const tabs = [
  { id: 'overview', label: '总结摘要' },
  { id: 'transcript', label: '字幕文本' },
  { id: 'mindmap', label: '思维导图' },
  { id: 'chat', label: 'AI 问答' },
]

const activeTab = ref('overview')
const summarizing = ref(false)
const completed = ref(false)
const progress = ref(0)
const taskStatus = ref('')
const statusDetail = ref('')
const error = ref('')
const result = ref(null)
const taskId = ref('')
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
  taskId.value = ''
  activeTab.value = 'overview'
}

async function pollTask(id) {
  try {
    const task = await getSummaryStatus(id)
    progress.value = task.progress || 0
    taskStatus.value = task.status
    statusDetail.value = task.status_detail || ''

    if (task.status === 'completed') {
      result.value = task.result
      taskId.value = id
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
    taskId.value = task_id
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
</script>
