<template>
  <div class="min-h-screen flex flex-col bg-surface-muted">
    <AppHeader />
    <p
      v-if="auth.banner"
      class="max-w-6xl mx-auto mt-4 px-4"
    >
      <span
        class="block text-sm rounded-xl px-4 py-3"
        :class="auth.bannerTone === 'error'
          ? 'bg-red-50 text-red-700'
          : 'bg-primary-light text-gray-800'"
      >
        {{ auth.banner }}
      </span>
    </p>

    <main class="flex-1">
      <HeroSection
        :loading="loading"
        :error="parseError"
        @parse="handleParse"
      />

      <section v-if="videoInfo" class="max-w-6xl mx-auto px-4 pb-8">
        <div class="grid grid-cols-1 lg:grid-cols-5 gap-4 lg:gap-5">
          <div class="lg:col-span-2 min-w-0">
            <VideoResult
              :video="videoInfo"
              :url="currentUrl"
              embedded
            />
          </div>
          <div class="lg:col-span-3 min-w-0">
            <SummaryPanelTabs
              :url="currentUrl"
              :title="videoInfo.title"
              embedded
            />
          </div>
        </div>
      </section>

      <PlatformGrid v-if="!videoInfo" />
      <SeoGuide />
    </main>

    <AppFooter />
    <AuthDialog v-if="auth.dialog === 'auth'" />
    <MembershipDialog v-if="auth.dialog === 'membership'" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { fetchVideoInfo } from './api/client'
import { auth, finishCheckoutReturn, refreshMe } from './auth/store'
import AppHeader from './components/AppHeader.vue'
import HeroSection from './components/HeroSection.vue'
import VideoResult from './components/VideoResult.vue'
import PlatformGrid from './components/PlatformGrid.vue'
import AppFooter from './components/AppFooter.vue'
import SummaryPanelTabs from './components/summary/SummaryPanelTabs.vue'
import SeoGuide from './components/SeoGuide.vue'
import AuthDialog from './components/AuthDialog.vue'
import MembershipDialog from './components/MembershipDialog.vue'

onMounted(async () => {
  await refreshMe()
  const params = new URLSearchParams(window.location.search)
  const billing = params.get('billing')
  if (!billing) return
  const sessionId = params.get('session_id') || ''
  window.history.replaceState({}, '', window.location.pathname)
  if (billing === 'cancel') {
    auth.banner = '已取消支付，没有扣款。'
    auth.bannerTone = 'info'
    auth.dialog = 'membership'
    return
  }
  if (billing === 'success') {
    await finishCheckoutReturn(sessionId)
  }
})

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
