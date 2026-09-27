<template>
  <footer class="border-t border-gray-200 bg-white mt-auto">
    <div class="max-w-5xl mx-auto px-4 py-8">
      <div class="text-center space-y-3">
        <nav class="flex flex-wrap items-center justify-center gap-x-6 gap-y-1 text-sm" aria-label="页脚导航">
          <a
            href="#product-definition"
            title="查看万能视频下载的产品说明"
            class="min-h-12 inline-flex items-center text-primary font-medium"
          >产品说明</a>
          <a
            href="#download-steps"
            title="查看在线视频下载步骤"
            class="min-h-12 inline-flex items-center text-primary font-medium"
          >下载步骤</a>
          <a
            href="#faq"
            title="查看视频下载常见问题"
            class="min-h-12 inline-flex items-center text-primary font-medium"
          >常见问题</a>
        </nav>
        <p class="text-sm text-gray-500 leading-relaxed max-w-xl mx-auto">
          本工具仅供个人学习研究使用，请尊重视频版权，勿用于商业用途。
          下载行为可能违反部分平台服务条款，请自行承担风险。
        </p>
        <div class="flex items-center justify-center gap-4 text-xs text-gray-400">
          <span>Powered by yt-dlp</span>
          <span>·</span>
          <span>FastAPI + Vue 3</span>
        </div>
      </div>
    </div>
  </footer>
</template>
