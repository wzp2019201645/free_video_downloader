<template>
  <div class="fixed inset-0 z-[70] flex items-center justify-center px-4 bg-black/40" @click.self="closeDialog">
    <div
      class="card w-full max-w-md p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="member-title"
    >
      <div class="flex items-center justify-between mb-4">
        <h2 id="member-title" class="text-lg font-bold text-gray-900">Pro 会员</h2>
        <button class="text-gray-400 hover:text-gray-600 text-xl leading-none" type="button" @click="closeDialog">
          ×
        </button>
      </div>

      <p class="text-2xl font-bold text-gray-900">{{ plan?.label || '每月 ¥19' }}</p>
      <p class="text-xs text-gray-500 mt-1">按月订阅，可随时在 Stripe 里取消。取消后可用到当前周期结束。</p>

      <ul class="mt-4 space-y-2 text-sm text-gray-700">
        <li>1080p、2K、4K 和「最佳质量」下载</li>
        <li>AI 总结、字幕导出、思维导图、问答</li>
        <li>720p 及以下、仅音频继续免费，不用登录</li>
      </ul>

      <div v-if="auth.user?.is_member" class="mt-4 p-3 rounded-xl bg-primary-light text-sm text-gray-800">
        <p>当前账号 {{ auth.user.email }} 已是 Pro。</p>
        <p v-if="until" class="mt-1 text-gray-600">
          {{ auth.user.cancel_at_period_end ? `将于 ${until} 到期后停止` : `当前周期到 ${until}` }}
        </p>
      </div>
      <p v-else-if="auth.user" class="mt-4 text-sm text-gray-600">
        将开通到账号 {{ auth.user.email }}。付款在 Stripe 页面完成，本站不保存卡号。
      </p>
      <p v-else class="mt-4 text-sm text-gray-600">请先注册或登录，再付款。会员跟账号走，不跟这台浏览器走。</p>

      <p v-if="!plan?.configured" class="mt-3 text-sm text-amber-700 bg-amber-50 rounded-xl px-3 py-2">
        这台后端还没配好 Stripe 测试密钥。请按说明填写 backend/.env 后重启后端，再点「去支付」。
      </p>
      <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>

      <div class="mt-5 flex flex-col gap-2">
        <button
          v-if="!auth.user"
          class="btn-primary w-full"
          type="button"
          @click="goLogin"
        >
          登录后购买
        </button>
        <button
          v-else-if="!auth.user.is_member"
          class="btn-primary w-full"
          type="button"
          :disabled="working"
          @click="pay"
        >
          {{ working ? '正在打开 Stripe…' : '去支付' }}
        </button>
        <button
          v-if="auth.user?.has_billing_customer"
          class="w-full px-6 py-2.5 rounded-full border border-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-50"
          type="button"
          :disabled="working"
          @click="manage"
        >
          管理或取消订阅
        </button>
        <button
          v-if="auth.user"
          class="text-sm text-gray-500 hover:text-gray-800"
          type="button"
          @click="logout"
        >
          退出登录
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { fetchPlan, startCheckout, startPortal } from '../api/authClient'
import { auth, closeDialog, errorText, logout, openAuth, refreshMe } from '../auth/store'
import { formatDate } from '../utils/membership'

const plan = ref(null)
const error = ref('')
const working = ref(false)

const until = computed(() => formatDate(auth.user?.current_period_end))

async function loadPlan() {
  try {
    plan.value = await fetchPlan()
  } catch (err) {
    error.value = errorText(err, '暂时读不到价格')
  }
}

function goLogin() {
  openAuth('membership')
}

async function pay() {
  error.value = ''
  working.value = true
  try {
    const url = await startCheckout()
    window.location.assign(url)
  } catch (err) {
    if (err?.response?.status === 409) await refreshMe()
    error.value = errorText(err, '暂时无法发起支付')
    working.value = false
  }
}

async function manage() {
  error.value = ''
  working.value = true
  try {
    const url = await startPortal()
    window.location.assign(url)
  } catch (err) {
    error.value = errorText(err, '暂时无法打开订阅管理')
    working.value = false
  }
}

function onKey(event) {
  if (event.key === 'Escape') closeDialog()
}

watch(() => auth.dialog, (dialog) => {
  if (dialog === 'membership') loadPlan()
})

onMounted(() => {
  window.addEventListener('keydown', onKey)
  loadPlan()
})
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>
