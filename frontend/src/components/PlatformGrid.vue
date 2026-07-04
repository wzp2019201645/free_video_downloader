<template>
  <section class="px-4 pb-12">
    <div class="max-w-5xl mx-auto">
      <h2 class="text-center text-lg font-semibold text-gray-700 mb-6">
        支持 1000+ 视频平台
      </h2>
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
        <div
          v-for="platform in platforms"
          :key="platform.name"
          class="card group hover:shadow-lg transition-shadow duration-200 cursor-default"
        >
          <div
            class="h-24 sm:h-28 flex items-center justify-center text-4xl sm:text-5xl"
            :style="{ background: platform.bg }"
          >
            {{ platform.icon }}
          </div>
          <div class="p-3 sm:p-4">
            <h3 class="font-semibold text-sm text-gray-900 mb-1.5">{{ platform.name }}</h3>
            <div class="flex flex-wrap gap-x-1">
              <span v-for="tag in platform.tags" :key="tag" class="tag"># {{ tag }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
const platforms = [
  { name: 'YouTube', icon: '▶️', bg: 'linear-gradient(135deg, #FF0000 0%, #CC0000 100%)', tags: ['4K', '播放列表'] },
  { name: '哔哩哔哩', icon: '📺', bg: 'linear-gradient(135deg, #FB7299 0%, #E85D88 100%)', tags: ['弹幕', '高清'] },
  { name: 'TikTok', icon: '🎵', bg: 'linear-gradient(135deg, #010101 0%, #25F4EE 100%)', tags: ['短视频', '无水印'] },
  { name: 'Twitter / X', icon: '🐦', bg: 'linear-gradient(135deg, #1DA1F2 0%, #0D8BD9 100%)', tags: ['推文视频'] },
  { name: 'Instagram', icon: '📷', bg: 'linear-gradient(135deg, #833AB4 0%, #FD1D1D 50%, #FCAF45 100%)', tags: ['Reels', 'Stories'] },
  { name: 'Facebook', icon: '👤', bg: 'linear-gradient(135deg, #1877F2 0%, #0D65D9 100%)', tags: ['公开视频'] },
  { name: 'Vimeo', icon: '🎬', bg: 'linear-gradient(135deg, #1AB7EA 0%, #0088CC 100%)', tags: ['专业视频'] },
  { name: '更多平台', icon: '🌐', bg: 'linear-gradient(135deg, #1677FF 0%, #0958D9 100%)', tags: ['1000+', '持续更新'] },
]
</script>
