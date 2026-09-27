<template>
  <section class="px-4 pb-16" aria-label="使用说明">
    <div class="max-w-5xl mx-auto">
      <p class="text-center text-sm sm:text-base text-gray-500 leading-relaxed max-w-3xl mx-auto">
        复制公开视频的链接，解析后选择清晰度，即可保存到手机或电脑。需要整理内容时，再生成 AI 摘要、字幕和思维导图。下载能力来自
        <a
          href="https://github.com/yt-dlp/yt-dlp"
          target="_blank"
          rel="noopener noreferrer"
          title="yt-dlp 开源下载项目"
          class="text-primary hover:text-primary-hover"
        >yt-dlp</a>。
      </p>
      <nav class="mt-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-1 text-sm" aria-label="说明导航">
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

      <section id="product-definition" class="card mt-8 p-5 sm:p-8 scroll-mt-20" aria-labelledby="about-title">
        <h2 id="about-title" class="text-lg font-semibold text-gray-900">{{ productDefinition.heading }}</h2>
        <p class="mt-3 text-sm sm:text-base text-gray-600 leading-relaxed">
          {{ productDefinition.summary }}
        </p>
      </section>

      <section id="download-steps" class="card mt-4 p-5 sm:p-8 scroll-mt-20">
        <h2 class="text-lg font-semibold text-gray-900">在线视频下载步骤</h2>
        <ol class="mt-6 space-y-5">
          <li v-for="(step, index) in steps" :key="step.title" class="flex gap-4">
            <span
              class="mt-0.5 w-8 h-8 shrink-0 rounded-full bg-primary text-white text-sm font-semibold inline-flex items-center justify-center"
              aria-hidden="true"
            >{{ index + 1 }}</span>
            <div>
              <h3 class="font-semibold text-gray-900">{{ step.title }}</h3>
              <p class="mt-1 text-sm text-gray-500 leading-relaxed">{{ step.body }}</p>
            </div>
          </li>
        </ol>
      </section>

      <section id="faq" class="card mt-4 p-5 sm:p-8 scroll-mt-20">
        <h2 class="text-lg font-semibold text-gray-900">视频下载常见问题</h2>
        <div class="mt-6 space-y-5">
          <article v-for="item in faqs" :key="item.question">
            <h3 class="text-sm sm:text-base font-semibold text-gray-900">{{ item.question }}</h3>
            <p class="mt-1 text-sm text-gray-500 leading-relaxed">{{ item.answer }}</p>
          </article>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { faqs, productDefinition, steps } from '../content/homeCopy.js'
</script>
