<template>
  <div class="min-h-screen flex flex-col bg-surface-muted">
    <AppHeader />

    <main class="flex-1">
      <HeroSection
        :loading="loading"
        :error="parseError"
        @parse="handleParse"
      />

      <VideoResult
        v-if="videoInfo"
        :video="videoInfo"
        :url="currentUrl"
      />

      <PlatformGrid v-if="!videoInfo" />
    </main>

    <AppFooter />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { fetchVideoInfo } from './api/client'
import AppHeader from './components/AppHeader.vue'
import HeroSection from './components/HeroSection.vue'
import VideoResult from './components/VideoResult.vue'
import PlatformGrid from './components/PlatformGrid.vue'
import AppFooter from './components/AppFooter.vue'

const loading = ref(false)
const parseError = ref('')
const videoInfo = ref(null)
const currentUrl = ref('')

async function handleParse(url) {
  loading.value = true
  parseError.value = ''
  videoInfo.value = null
  currentUrl.value = url

  try {
    videoInfo.value = await fetchVideoInfo(url)
    currentUrl.value = videoInfo.value.webpage_url || url
  } catch (err) {
    parseError.value = err.response?.data?.detail || '解析失败，请检查链接是否正确'
  } finally {
    loading.value = false
  }
}
</script>
