<template>
  <div class="flex flex-col h-[28rem]">
    <div ref="scrollRef" class="flex-1 overflow-y-auto space-y-4 pr-1 mb-4">
      <div
        v-if="!messages.length"
        class="h-full flex items-center justify-center text-center px-4"
      >
        <div>
          <p class="text-sm text-gray-600 mb-1">基于视频内容智能问答</p>
          <p class="text-xs text-gray-400">例如：「视频的核心结论是什么？」「第 3 分钟讲了什么？」</p>
        </div>
      </div>

      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="flex"
        :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="max-w-[85%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed"
          :class="msg.role === 'user'
            ? 'bg-primary text-white rounded-br-md'
            : 'bg-gray-100 text-gray-800 rounded-bl-md'"
        >
          {{ msg.content }}
        </div>
      </div>

      <div v-if="loading" class="flex justify-start">
        <div class="px-4 py-2.5 rounded-2xl bg-gray-100 text-sm text-gray-500 rounded-bl-md">
          思考中…
        </div>
      </div>
    </div>

    <div v-if="error" class="mb-2 text-xs text-red-500">{{ error }}</div>

    <form class="flex gap-2" @submit.prevent="handleSend">
      <input
        v-model="input"
        type="text"
        class="flex-1 px-4 py-2.5 rounded-full border border-gray-200 text-sm
               focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
        placeholder="输入你的问题…"
        :disabled="loading || !taskId"
      />
      <button
        type="submit"
        class="btn-primary px-5 py-2.5 text-sm shrink-0"
        :disabled="loading || !input.trim() || !taskId"
      >
        发送
      </button>
    </form>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { sendSummaryChat } from '../../../api/summaryExtendedClient'

const props = defineProps({
  taskId: { type: String, required: true },
})

const messages = ref([])
const input = ref('')
const loading = ref(false)
const error = ref('')
const scrollRef = ref(null)

async function scrollToBottom() {
  await nextTick()
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  }
}

async function handleSend() {
  const text = input.value.trim()
  if (!text || !props.taskId || loading.value) return

  error.value = ''
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  await scrollToBottom()

  try {
    const history = messages.value.slice(0, -1)
    const { reply } = await sendSummaryChat(props.taskId, text, history)
    messages.value.push({ role: 'assistant', content: reply })
  } catch (err) {
    error.value = err.response?.data?.detail || 'AI 问答失败'
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

watch(
  () => props.taskId,
  () => {
    messages.value = []
    input.value = ''
    error.value = ''
  },
)
</script>
