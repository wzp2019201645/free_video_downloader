<template>
  <component :is="embedded ? 'div' : 'section'" :class="embedded ? '' : 'px-4 pb-8'">
    <div :class="embedded ? '' : 'max-w-3xl mx-auto'">
      <div class="card p-4 sm:p-5">
        <!-- 封面预览 -->
        <div class="w-full">
          <img
            v-if="thumbnailSrc"
            :src="thumbnailSrc"
            :alt="video.title"
            class="w-full h-auto rounded-lg object-cover aspect-video bg-gray-100"
            @error="onThumbnailError"
          />
          <div
            v-else
            class="w-full aspect-video rounded-lg bg-gray-100 flex items-center justify-center"
          >
            <svg class="w-12 h-12 text-gray-300" fill="currentColor" viewBox="0 0 24 24">
              <path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/>
            </svg>
          </div>
        </div>

        <!-- 标题与元信息 -->
        <div class="mt-4">
          <h2 class="text-base font-bold text-gray-900 line-clamp-2 mb-2">{{ video.title }}</h2>
          <div class="flex flex-wrap gap-x-2 gap-y-1">
            <span v-if="video.uploader" class="tag"># {{ video.uploader }}</span>
            <span v-if="video.duration" class="tag"># {{ formatDuration(video.duration) }}</span>
            <span class="tag"># {{ video.formats.length }} 种格式</span>
          </div>
        </div>

        <!-- 紧凑清晰度选择 -->
        <div class="mt-4">
          <label class="block text-xs font-semibold text-gray-700 mb-1.5" for="format-select">
            清晰度 / 格式
          </label>
          <select
            id="format-select"
            v-model="selectedFormat"
            class="w-full rounded-xl border border-gray-200 bg-gray-50/80 px-3 py-2.5 text-sm text-gray-900
                   focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
          >
            <option
              v-for="fmt in video.formats"
              :key="fmt.format_id"
              :value="fmt.format_id"
            >
              {{ fmt.quality }} · .{{ fmt.ext }}<template v-if="fmt.filesize"> · {{ formatSize(fmt.filesize) }}</template>
            </option>
          </select>
        </div>

        <!-- 下载按钮 -->
        <div class="mt-4">
          <button
            class="btn-primary w-full py-2.5 text-sm"
            :disabled="!selectedFormat || downloading"
            @click="handleDownload"
          >
            <span v-if="downloading">下载中 {{ progress }}%</span>
            <span v-else>下载到本地</span>
          </button>
        </div>

        <!-- 进度条 -->
        <DownloadProgress
          v-if="downloading || downloadComplete || taskError"
          :progress="progress"
          :status="taskStatus"
          :filename="taskFilename"
          :task-id="taskId"
          :saved="saved"
          :error="taskError"
          @saved="onSaved"
          @save-error="onSaveError"
        />
      </div>
    </div>
  </component>
</template>

<script setup>
import { computed, ref } from 'vue'
import { startDownload, getTaskStatus, getThumbnailUrl } from '../api/client'
import DownloadProgress from './DownloadProgress.vue'

const props = defineProps({
  video: { type: Object, required: true },
  url: { type: String, required: true },
  embedded: { type: Boolean, default: false },
})

const selectedFormat = ref(
  props.video.formats.length ? props.video.formats[0].format_id : ''
)
const downloading = ref(false)
const downloadComplete = ref(false)
const progress = ref(0)
const taskStatus = ref('')
const taskFilename = ref('')
const taskId = ref('')
const taskError = ref('')
const saved = ref(false)
const thumbnailFailed = ref(false)
let pollTimer = null

const thumbnailSrc = computed(() => {
  if (thumbnailFailed.value || !props.video.thumbnail) return ''
  return getThumbnailUrl(props.video.thumbnail)
})

function onThumbnailError() {
  thumbnailFailed.value = true
}

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB'
  return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB'
}

function onSaved() {
  saved.value = true
}

function onSaveError(msg) {
  taskError.value = msg
}

async function pollTask(currentTaskId) {
  try {
    const task = await getTaskStatus(currentTaskId)
    progress.value = task.progress
    taskStatus.value = task.status
    taskFilename.value = task.filename || ''

    if (task.status === 'completed') {
      downloading.value = false
      downloadComplete.value = true
      return true
    }
    if (task.status === 'failed') {
      downloading.value = false
      taskError.value = task.error || '下载失败'
      return true
    }
    return false
  } catch {
    downloading.value = false
    taskError.value = '查询进度失败'
    return true
  }
}

async function handleDownload() {
  if (!selectedFormat.value) return
  downloading.value = true
  downloadComplete.value = false
  progress.value = 0
  taskError.value = ''
  taskId.value = ''
  saved.value = false
  if (pollTimer) clearInterval(pollTimer)

  try {
    const { task_id } = await startDownload(props.url, selectedFormat.value)
    taskId.value = task_id

    pollTimer = setInterval(async () => {
      const done = await pollTask(task_id)
      if (done) clearInterval(pollTimer)
    }, 1000)
  } catch (err) {
    downloading.value = false
    taskError.value = err.response?.data?.detail || '创建下载任务失败'
  }
}
</script>
