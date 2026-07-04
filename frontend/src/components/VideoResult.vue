<template>
  <section class="px-4 pb-8">
    <div class="max-w-3xl mx-auto">
      <div class="card p-5 sm:p-6">
        <!-- 视频信息 -->
        <div class="flex flex-col sm:flex-row gap-5">
          <div class="shrink-0 mx-auto sm:mx-0">
            <img
              v-if="thumbnailSrc"
              :src="thumbnailSrc"
              :alt="video.title"
              class="w-full sm:w-48 h-auto rounded-lg object-cover aspect-video bg-gray-100"
              @error="onThumbnailError"
            />
            <div v-else class="w-full sm:w-48 aspect-video rounded-lg bg-gray-100 flex items-center justify-center">
              <svg class="w-12 h-12 text-gray-300" fill="currentColor" viewBox="0 0 24 24">
                <path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z"/>
              </svg>
            </div>
          </div>
          <div class="flex-1 min-w-0">
            <h2 class="text-lg font-bold text-gray-900 line-clamp-2 mb-2">{{ video.title }}</h2>
            <div class="flex flex-wrap gap-2 mb-4">
              <span v-if="video.uploader" class="tag"># {{ video.uploader }}</span>
              <span v-if="video.duration" class="tag"># {{ formatDuration(video.duration) }}</span>
              <span class="tag"># {{ video.formats.length }} 种格式</span>
            </div>
          </div>
        </div>

        <!-- 格式选择 -->
        <div class="mt-6">
          <h3 class="text-sm font-semibold text-gray-700 mb-3">选择清晰度 / 格式</h3>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            <button
              v-for="fmt in video.formats"
              :key="fmt.format_id"
              class="relative p-3 rounded-xl border-2 text-left transition-all duration-150"
              :class="selectedFormat === fmt.format_id
                ? 'border-primary bg-primary-light'
                : 'border-gray-100 hover:border-gray-200 bg-gray-50/50'"
              @click="selectedFormat = fmt.format_id"
            >
              <div class="font-semibold text-sm text-gray-900">{{ fmt.quality }}</div>
              <div class="text-xs text-gray-500 mt-0.5">
                .{{ fmt.ext }}
                <span v-if="fmt.filesize"> · {{ formatSize(fmt.filesize) }}</span>
              </div>
              <div
                v-if="selectedFormat === fmt.format_id"
                class="absolute top-2 right-2 w-5 h-5 bg-primary rounded-full flex items-center justify-center"
              >
                <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
            </button>
          </div>
        </div>

        <!-- 下载按钮 -->
        <div class="mt-6 flex flex-col sm:flex-row gap-3">
          <button
            class="btn-primary flex-1 py-3 text-base"
            :disabled="!selectedFormat || downloading"
            @click="handleDownload"
          >
            <span v-if="downloading">下载中 {{ progress }}%</span>
            <span v-else>下载到本地</span>
          </button>
          <button
            class="px-6 py-3 rounded-full border border-gray-200 text-gray-500 text-sm
                   hover:bg-gray-50 transition-colors opacity-50 cursor-not-allowed"
            title="即将上线（第二期）"
          >
            AI 总结
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
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { startDownload, getTaskStatus, getThumbnailUrl } from '../api/client'
import DownloadProgress from './DownloadProgress.vue'

const props = defineProps({
  video: { type: Object, required: true },
  url: { type: String, required: true },
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
