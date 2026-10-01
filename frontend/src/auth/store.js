import { reactive } from 'vue'
import {
  confirmCheckout,
  errorText,
  fetchMe,
  loginAccount,
  logoutAccount,
  registerAccount,
} from '../api/authClient'

export const auth = reactive({
  loaded: false,
  user: null,
  dialog: '',
  afterAuth: '',
  banner: '',
  bannerTone: 'info',
})

export function openAuth(afterAuth = '') {
  auth.afterAuth = afterAuth
  auth.dialog = 'auth'
}

export function openMembership() {
  auth.dialog = 'membership'
}

export function closeDialog() {
  auth.dialog = ''
  auth.afterAuth = ''
}

export async function refreshMe() {
  try {
    auth.user = await fetchMe()
  } catch {
    auth.user = null
  } finally {
    auth.loaded = true
  }
}

export async function submitAuth(mode, email, password) {
  const user = mode === 'register'
    ? await registerAccount(email, password)
    : await loginAccount(email, password)
  auth.user = user
  if (auth.afterAuth === 'membership' && !user.is_member) {
    auth.dialog = 'membership'
    auth.afterAuth = ''
    return
  }
  closeDialog()
}

export async function logout() {
  await logoutAccount()
  auth.user = null
  closeDialog()
  auth.banner = '已退出登录'
  auth.bannerTone = 'info'
}

export async function finishCheckoutReturn(sessionId) {
  if (!auth.user) {
    auth.banner = '支付页面已返回。请登录刚才付款的账号，会员会记在这个账号上。'
    auth.bannerTone = 'info'
    openAuth('membership')
    return
  }
  auth.dialog = 'membership'
  auth.banner = '正在向 Stripe 确认这笔付款…'
  auth.bannerTone = 'info'
  try {
    if (sessionId) {
      auth.user = await confirmCheckout(sessionId)
    }
    if (!auth.user?.is_member) {
      for (let i = 0; i < 4; i += 1) {
        await new Promise((resolve) => setTimeout(resolve, 1000))
        await refreshMe()
        if (auth.user?.is_member) break
      }
    }
    if (auth.user?.is_member) {
      auth.banner = 'Pro 会员已开通。1080p 及以上和 AI 功能现在可以使用。'
      auth.bannerTone = 'info'
    } else {
      auth.banner = '还没有确认到会员。请保持 stripe listen 窗口开着，等几秒后刷新页面。'
      auth.bannerTone = 'error'
    }
  } catch (err) {
    auth.banner = errorText(err, '确认支付失败')
    auth.bannerTone = 'error'
  }
}

export { errorText }
