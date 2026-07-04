<template>
  <div class="mt-5 p-4 rounded-xl bg-gray-50 border border-gray-100">
    <div v-if="status === 'downloading' || (progress > 0 && progress < 100 && status !== 'completed')" class="mb-3">
      <div class="flex justify-between text-xs text-gray-500 mb-1.5">
        <span>下载进度</span>
        <span>{{ progress.toFixed(1) }}%</span>
      </div>
      <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          class="h-full bg-primary rounded-full transition-all duration-300 ease-out"
          :style="{ width: progress + '%' }"
        />
      </div>
    </div>

    <div v-if="status === 'completed' && taskId" class="flex flex-col sm:flex-row sm:items-center gap-3">
      <div class="flex items-center gap-3 flex-1 min-w-0">
        <div class="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center shrink-0">
          <svg class="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-gray-900 truncate">{{ filename }}</p>
          <p class="text-xs text-gray-500">
            {{ isSaved ? '已保存到所选位置' : '下载完成，请选择保存位置' }}
          </p>
        </div>
      </div>
      <button
        type="button"
        class="btn-primary text-sm shrink-0 w-full sm:w-auto"
        :disabled="saving"
        @click="handleSave"
      >
        {{ saving ? '保存中...' : '选择保存位置' }}
      </button>
    </div>

    <div v-if="error" class="flex items-center gap-3">
      <div class="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center shrink-0">
        <svg class="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
        </svg>
      </div>
      <p class="text-sm text-red-600">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { saveFileToDisk } from '../api/client'

const props = defineProps({
  progress: { type: Number, default: 0 },
  status: { type: String, default: '' },
  filename: { type: String, default: '' },
  taskId: { type: String, default: '' },
  error: { type: String, default: '' },
  saved: { type: Boolean, default: false },
})

const emit = defineEmits(['saved', 'save-error'])

const saving = ref(false)
const isSaved = ref(props.saved)

watch(() => props.saved, (v) => { isSaved.value = v })

function handleSave() {
  if (!props.taskId || saving.value) return

  // Start save synchronously so showSaveFilePicker runs inside the click gesture
  const promise = saveFileToDisk(props.taskId, props.filename)
  saving.value = true

  promise
    .then(() => {
      isSaved.value = true
      emit('saved')
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        emit('save-error', err.message || '保存失败')
      }
    })
    .finally(() => {
      saving.value = false
    })
}
</script>
