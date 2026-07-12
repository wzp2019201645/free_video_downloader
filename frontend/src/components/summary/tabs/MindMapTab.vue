<template>
  <div>
    <div v-if="loading" class="py-12 text-center">
      <p class="text-sm text-gray-500">DeepSeek 正在生成思维导图…</p>
      <div class="mt-3 h-1.5 max-w-xs mx-auto bg-gray-200 rounded-full overflow-hidden">
        <div class="h-full bg-primary rounded-full animate-pulse w-2/3" />
      </div>
    </div>

    <div v-else-if="error" class="p-4 rounded-xl bg-red-50 border border-red-100">
      <p class="text-sm text-red-600 mb-3">{{ error }}</p>
      <button class="btn-primary px-4 py-2 text-sm" @click="loadMindMap">重试</button>
    </div>

    <div v-else-if="mindMap" class="overflow-x-auto py-4">
      <MindMapTree :node="mindMap.root" />
    </div>

    <div v-else class="py-12 text-center">
      <p class="text-sm text-gray-500 mb-4">基于 AI 总结自动生成结构化思维导图</p>
      <button class="btn-primary px-6 py-2.5 text-sm" @click="loadMindMap">生成思维导图</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { generateMindMap } from '../../../api/summaryExtendedClient'
import MindMapTree from '../MindMapTree.vue'

const props = defineProps({
  taskId: { type: String, required: true },
  active: { type: Boolean, default: false },
})

const loading = ref(false)
const error = ref('')
const mindMap = ref(null)
const autoLoaded = ref(false)

async function loadMindMap() {
  if (!props.taskId || loading.value) return
  loading.value = true
  error.value = ''
  try {
    mindMap.value = await generateMindMap(props.taskId)
  } catch (err) {
    error.value = err.response?.data?.detail || '思维导图生成失败'
  } finally {
    loading.value = false
  }
}

watch(
  () => props.active,
  (isActive) => {
    if (isActive && !autoLoaded.value && !mindMap.value && props.taskId) {
      autoLoaded.value = true
      loadMindMap()
    }
  },
  { immediate: true },
)

watch(
  () => props.taskId,
  () => {
    mindMap.value = null
    autoLoaded.value = false
    error.value = ''
  },
)
</script>
