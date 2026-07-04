<template>
  <header class="sticky top-0 z-50 bg-white/90 backdrop-blur-sm border-b border-gray-100">
    <div class="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <button class="md:hidden p-1.5 rounded-lg hover:bg-gray-100" aria-label="菜单">
          <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
            </svg>
          </div>
          <span class="font-semibold text-gray-900 hidden sm:block">万能视频下载</span>
        </div>
      </div>
      <button
        class="flex items-center gap-1.5 px-4 py-1.5 rounded-full border border-primary/30
               text-primary text-sm font-medium opacity-60 cursor-not-allowed"
        title="即将上线"
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
        </svg>
        Pro 会员
      </button>
    </div>
  </header>
</template>
