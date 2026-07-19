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

    <div v-else-if="mindMap" class="space-y-3">
      <div class="flex flex-wrap items-center justify-end gap-2">
        <button
          type="button"
          class="text-xs text-primary hover:underline disabled:opacity-50"
          :disabled="!!exporting"
          @click="exportSvg"
        >
          {{ exporting === 'svg' ? '导出中…' : '下载 SVG' }}
        </button>
        <button
          type="button"
          class="text-xs text-primary hover:underline disabled:opacity-50"
          :disabled="!!exporting"
          @click="exportPng"
        >
          {{ exporting === 'png' ? '导出中…' : '下载高清 PNG' }}
        </button>
      </div>
      <p v-if="exportError" class="text-xs text-red-500 text-right">{{ exportError }}</p>
      <div
        ref="containerRef"
        class="markmap-container w-full overflow-hidden rounded-xl border border-gray-100 bg-white"
      >
        <svg ref="svgRef" class="w-full h-full block" />
      </div>
    </div>

    <div v-else class="py-12 text-center">
      <p class="text-sm text-gray-500 mb-4">基于 AI 总结自动生成结构化思维导图</p>
      <button class="btn-primary px-6 py-2.5 text-sm" @click="loadMindMap">生成思维导图</button>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { Transformer } from 'markmap-lib'
import { Markmap, loadCSS, loadJS } from 'markmap-view'
import { generateMindMap } from '../../../api/summaryExtendedClient'
import {
  buildExportableSvgString,
  saveBlobAsFile,
  svgStringToBlob,
  svgStringToPngBlob,
} from '../../../utils/mindmapExport'
import { mindMapTreeToMarkdown } from '../../../utils/mindmapMarkdown'

const props = defineProps({
  taskId: { type: String, required: true },
  active: { type: Boolean, default: false },
  title: { type: String, default: '' },
})

const loading = ref(false)
const error = ref('')
const exportError = ref('')
const mindMap = ref(null)
const autoLoaded = ref(false)
const exporting = ref('')
const svgRef = ref(null)
const containerRef = ref(null)

let markmapInstance = null
const transformer = new Transformer()

async function ensureAssets(features) {
  const { styles, scripts } = transformer.getUsedAssets(features)
  if (styles?.length) loadCSS(styles)
  if (scripts?.length) await loadJS(scripts)
}

async function renderMarkmap() {
  await nextTick()
  if (!mindMap.value?.root || !svgRef.value) return

  const markdown = mindMapTreeToMarkdown(mindMap.value.root)
  const { root, features } = transformer.transform(markdown)
  await ensureAssets(features)

  if (!markmapInstance) {
    markmapInstance = new Markmap(svgRef.value, {
      zoom: true,
      pan: true,
      duration: 300,
    })
  }
  await markmapInstance.setData(root)
  await markmapInstance.fit()
}

function destroyMarkmap() {
  markmapInstance = null
  if (svgRef.value) {
    while (svgRef.value.firstChild) {
      svgRef.value.removeChild(svgRef.value.firstChild)
    }
  }
}

async function loadMindMap() {
  if (!props.taskId || loading.value) return
  loading.value = true
  error.value = ''
  try {
    mindMap.value = await generateMindMap(props.taskId)
    await renderMarkmap()
  } catch (err) {
    error.value = err.response?.data?.detail || '思维导图生成失败'
    destroyMarkmap()
  } finally {
    loading.value = false
  }
}

function fileBase() {
  return props.title || 'mindmap'
}

async function safeFit() {
  if (!markmapInstance?.fit) return
  try {
    await Promise.race([
      markmapInstance.fit(),
      new Promise((resolve) => setTimeout(resolve, 1500)),
    ])
  } catch {
    // ignore fit failures; export can still proceed
  }
}

async function exportSvg() {
  if (!svgRef.value || exporting.value) return
  exporting.value = 'svg'
  exportError.value = ''
  try {
    // Open save dialog immediately to preserve user gesture (Chromium)
    const result = await saveBlobAsFile({
      filename: fileBase(),
      mimeType: 'image/svg+xml',
      description: 'SVG 图片',
      extension: '.svg',
      buildBlob: async () => {
        await safeFit()
        await nextTick()
        const svgText = buildExportableSvgString(svgRef.value)
        return svgStringToBlob(svgText)
      },
    })
    if (result?.cancelled) return
  } catch (err) {
    exportError.value = err?.message || '下载 SVG 失败'
  } finally {
    exporting.value = ''
  }
}

async function exportPng() {
  if (!svgRef.value || exporting.value) return
  exporting.value = 'png'
  exportError.value = ''
  try {
    const result = await saveBlobAsFile({
      filename: fileBase(),
      mimeType: 'image/png',
      description: 'PNG 图片',
      extension: '.png',
      buildBlob: async () => {
        await safeFit()
        await nextTick()
        const svgText = buildExportableSvgString(svgRef.value)
        return svgStringToPngBlob(svgText, 3)
      },
    })
    if (result?.cancelled) return
  } catch (err) {
    exportError.value = err?.message || '下载高清 PNG 失败'
  } finally {
    exporting.value = ''
  }
}

watch(
  () => props.active,
  async (isActive) => {
    if (isActive && !autoLoaded.value && !mindMap.value && props.taskId) {
      autoLoaded.value = true
      await loadMindMap()
    } else if (isActive && mindMap.value) {
      await renderMarkmap()
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
    exportError.value = ''
    destroyMarkmap()
  },
)

onBeforeUnmount(() => {
  destroyMarkmap()
})
</script>

<style scoped>
.markmap-container {
  height: min(28rem, 70vh);
  min-height: 20rem;
}
</style>
