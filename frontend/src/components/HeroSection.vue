<template>
  <section class="pt-10 pb-8 px-4">
    <div class="max-w-3xl mx-auto text-center">
      <h1 class="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 leading-tight mb-4">
        万能视频下载，<span class="text-primary">一键保存</span>
      </h1>
      <p class="text-gray-500 text-base sm:text-lg mb-8">
        支持 YouTube / B站 / TikTok 等 1000+ 平台，粘贴链接即可下载到本地
      </p>

      <!-- 胶囊搜索栏 -->
      <div class="relative max-w-2xl mx-auto">
        <div
          class="flex items-center bg-white rounded-full shadow-input border border-gray-100
                 pl-5 pr-1.5 py-1.5 focus-within:ring-2 focus-within:ring-primary/20 transition-shadow"
        >
          <svg class="w-5 h-5 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <input
            v-model="inputUrl"
            type="url"
            placeholder="粘贴视频链接，例如 https://www.youtube.com/watch?v=..."
            class="flex-1 px-3 py-2.5 bg-transparent outline-none text-sm sm:text-base
                   placeholder:text-gray-400 min-w-0"
            @keydown.enter="handleSubmit"
            :disabled="loading"
          />
          <button
            class="btn-primary shrink-0 text-sm sm:text-base"
            :disabled="loading || !inputUrl.trim()"
            @click="handleSubmit"
          >
            <span v-if="loading" class="flex items-center gap-2">
              <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              解析中
            </span>
            <span v-else>解析</span>
          </button>
        </div>
        <p v-if="error" class="mt-3 text-sm text-red-500 text-left px-2 whitespace-pre-line">{{ error }}</p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  loading: Boolean,
  error: String,
})

const emit = defineEmits(['parse'])

const inputUrl = ref('')

function handleSubmit() {
  const url = inputUrl.value.trim()
  if (url) emit('parse', url)
}

defineExpose({ inputUrl })
</script>
