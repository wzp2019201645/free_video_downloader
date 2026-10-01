<template>
  <div class="fixed inset-0 z-[70] flex items-center justify-center px-4 bg-black/40" @click.self="closeDialog">
    <div
      class="card w-full max-w-md p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-title"
    >
      <div class="flex items-center justify-between mb-5">
        <h2 id="auth-title" class="text-lg font-bold text-gray-900">
          {{ mode === 'login' ? '登录' : '注册' }}
        </h2>
        <button class="text-gray-400 hover:text-gray-600 text-xl leading-none" type="button" @click="closeDialog">
          ×
        </button>
      </div>
      <p class="text-sm text-gray-500 mb-4">
        会员记在这个邮箱上。换电脑登录后，Pro 仍然在。
      </p>
      <form @submit.prevent="submit">
        <label class="block text-xs font-semibold text-gray-700 mb-1.5" for="auth-email">邮箱</label>
        <input
          id="auth-email"
          v-model="email"
          type="email"
          autocomplete="username"
          required
          class="w-full rounded-xl border border-gray-200 bg-gray-50/80 px-3 py-2.5 text-sm mb-3
                 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
        />
        <label class="block text-xs font-semibold text-gray-700 mb-1.5" for="auth-password">密码</label>
        <input
          id="auth-password"
          v-model="password"
          type="password"
          :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
          minlength="8"
          maxlength="128"
          required
          class="w-full rounded-xl border border-gray-200 bg-gray-50/80 px-3 py-2.5 text-sm
                 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
        />
        <p class="text-xs text-gray-400 mt-1.5">至少 8 位。网站不会看到银行卡号。</p>
        <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>
        <button class="btn-primary w-full mt-4" type="submit" :disabled="submitting">
          {{ submitting ? '请稍候…' : (mode === 'login' ? '登录' : '注册并登录') }}
        </button>
      </form>
      <button
        class="mt-4 text-sm text-primary hover:underline"
        type="button"
        @click="toggle"
      >
        {{ mode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { closeDialog, errorText, submitAuth } from '../auth/store'

const mode = ref('login')
const email = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

function toggle() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  error.value = ''
}

async function submit() {
  error.value = ''
  submitting.value = true
  try {
    await submitAuth(mode.value, email.value.trim(), password.value)
  } catch (err) {
    error.value = errorText(err, mode.value === 'login' ? '登录失败' : '注册失败')
  } finally {
    submitting.value = false
  }
}

function onKey(event) {
  if (event.key === 'Escape') closeDialog()
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>
