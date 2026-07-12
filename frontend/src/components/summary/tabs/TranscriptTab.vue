<template>
  <div>
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs text-gray-500">共 {{ result.transcript?.length || 0 }} 段</p>
      <button
        class="text-xs text-primary hover:underline"
        :disabled="copying"
        @click="handleCopyTranscript"
      >
        {{ copied ? '已复制' : '复制全文' }}
      </button>
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
import { ref } from 'vue'
import { formatTimestampForDisplay } from '../../../api/summaryClient'

const props = defineProps({
  result: { type: Object, required: true },
})

const emit = defineEmits(['error'])

const copying = ref(false)
const copied = ref(false)

function formatTs(seconds) {
  return formatTimestampForDisplay(seconds)
}

async function handleCopyTranscript() {
  if (!props.result.transcript?.length || copying.value) return
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
</script>
