import { faqs, productDefinition, steps } from './src/content/homeCopy.js'

export const siteName = '万能视频下载'

export const seoTitle =
  '免费视频下载 - 万能视频下载 | 粘贴链接保存到本地并生成 AI 总结 · 支持 YouTube 与 B站'

export const seoDescription =
  '万能视频下载支持 YouTube、哔哩哔哩、TikTok 等 1000 多个平台的公开视频。粘贴链接并选择清晰度，即可把视频保存到手机或电脑，也可以生成 AI 摘要、字幕和思维导图。适合学习、收藏和整理内容，无需安装软件，打开浏览器立即免费使用。解析完成后可以更换清晰度，页面若提供音频格式也可以单独保存。学习公开课程或收藏分享视频时，直接打开浏览器就能完成。'

export const seoKeywords = [
  '视频下载',
  '万能视频下载',
  'YouTube下载',
  'B站视频下载',
  'TikTok下载',
  '在线视频下载',
  'AI视频总结',
  '字幕下载',
  '免费视频下载',
  '手机下载视频',
].join(',')

const shareImagePath = '/video-download-share.png'

export function getSiteUrl() {
  return String(process.env.VITE_SITE_URL || '').trim().replace(/\/$/, '')
}

export function renderSeoHead() {
  const keywords = seoKeywords.split(',')
  if (keywords.length > 10) {
    throw new Error(`关键词不能超过 10 个，当前为 ${keywords.length} 个`)
  }
  if ([...seoTitle].length > 70) {
    throw new Error(`标题超过 70 个字符：${[...seoTitle].length}`)
  }

  const siteUrl = getSiteUrl()
  const pageUrl = siteUrl ? `${siteUrl}/` : ''
  const imageUrl = siteUrl ? `${siteUrl}${shareImagePath}` : ''

  const llmsHref = siteUrl ? `${siteUrl}/llms.txt` : '/llms.txt'

  const tags = [
    `<title>${escapeHtml(seoTitle)}</title>`,
    `<meta name="description" content="${escapeHtml(seoDescription)}" />`,
    `<meta name="keywords" content="${escapeHtml(seoKeywords)}" />`,
    '<meta name="robots" content="index, follow" />',
    '<meta http-equiv="content-language" content="zh-CN" />',
    `<link rel="alternate" type="text/plain" href="${escapeHtml(llmsHref)}" title="llms.txt" />`,
  ]

  if (pageUrl) {
    tags.push(`<link rel="canonical" href="${escapeHtml(pageUrl)}" />`)
  }

  tags.push(
    `<meta property="og:title" content="${escapeHtml(seoTitle)}" />`,
    `<meta property="og:description" content="${escapeHtml(seoDescription)}" />`,
    '<meta property="og:type" content="website" />',
    '<meta property="og:locale" content="zh_CN" />',
    `<meta property="og:site_name" content="${escapeHtml(siteName)}" />`,
  )

  if (pageUrl) {
    tags.push(`<meta property="og:url" content="${escapeHtml(pageUrl)}" />`)
  }
  if (imageUrl) {
    tags.push(
      `<meta property="og:image" content="${escapeHtml(imageUrl)}" />`,
      '<meta property="og:image:width" content="1200" />',
      '<meta property="og:image:height" content="630" />',
      `<meta itemprop="image" content="${escapeHtml(imageUrl)}" />`,
    )
  }

  tags.push(
    `<meta name="twitter:card" content="${imageUrl ? 'summary_large_image' : 'summary'}" />`,
    `<meta name="twitter:title" content="${escapeHtml(seoTitle)}" />`,
    `<meta name="twitter:description" content="${escapeHtml(seoDescription)}" />`,
  )
  if (imageUrl) {
    tags.push(`<meta name="twitter:image" content="${escapeHtml(imageUrl)}" />`)
  }

  tags.push(
    `<meta itemprop="name" content="${escapeHtml(siteName)}" />`,
    `<meta itemprop="description" content="${escapeHtml(seoDescription)}" />`,
    `<script type="application/ld+json">${renderJsonLd(pageUrl, imageUrl)}</script>`,
  )

  return tags.join('\n    ')
}

const aiCrawlers = [
  '*',
  'GPTBot',
  'OAI-SearchBot',
  'ChatGPT-User',
  'ClaudeBot',
  'Claude-SearchBot',
  'PerplexityBot',
  'Google-Extended',
  'Applebot-Extended',
  'Bytespider',
  'Amazonbot',
  'meta-externalagent',
]

export function renderRobotsTxt(siteUrl = getSiteUrl()) {
  const lines = [
    '# 允许搜索引擎和 AI 对话抓取公开页面。/api/ 是任务接口，不提供可引用内容。',
    ...aiCrawlers.map((name) => `User-agent: ${name}`),
    'Allow: /',
    'Disallow: /api/',
    '',
  ]
  if (siteUrl) {
    lines.push(`Sitemap: ${siteUrl}/sitemap.xml`, '')
  }
  return lines.join('\n')
}

export function renderLlmsTxt(siteUrl = getSiteUrl()) {
  const home = siteUrl ? `${siteUrl}/` : '/'
  const lines = [
    `# ${siteName}`,
    '',
    `> ${productDefinition.summary}`,
    '',
    '以下说明与网页正文一致，供 AI 助手引用。/api/ 只负责解析、下载和总结任务，不是可引用内容。',
    '',
    '## 使用步骤',
    ...steps.map((step, index) => `- ${index + 1}. ${step.title}：${step.body}`),
    '',
    '## 常见问题',
    ...faqs.flatMap((item) => [`- **${item.question}**`, `  ${item.answer}`]),
    '',
    '## 页面',
    `- [首页](${home})：粘贴视频链接，选择清晰度后保存到本地，并按需生成 AI 总结。`,
    `- [产品说明](${home}#product-definition)：${productDefinition.summary}`,
    `- [下载步骤](${home}#download-steps)：从复制链接到保存文件、生成总结的操作顺序。`,
    `- [常见问题](${home}#faq)：平台范围、手机下载、AI 总结、音频、文件保留时间和版权说明。`,
    '',
  ]
  return lines.join('\n')
}

export function renderSitemap(siteUrl = getSiteUrl()) {
  if (!siteUrl) {
    return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
</urlset>
`
  }

  const lastmod = new Date().toISOString().slice(0, 10)
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>${siteUrl}/</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
`
}

function renderJsonLd(pageUrl, imageUrl) {
  const website = {
    '@type': 'WebSite',
    name: siteName,
    inLanguage: 'zh-CN',
    description: productDefinition.summary,
  }
  if (pageUrl) {
    website.url = pageUrl
    website['@id'] = `${pageUrl}#website`
  }

  const webPage = {
    '@type': 'WebPage',
    name: siteName,
    inLanguage: 'zh-CN',
    description: productDefinition.summary,
    speakable: {
      '@type': 'SpeakableSpecification',
      cssSelector: ['#product-definition'],
    },
  }
  if (pageUrl) {
    webPage.url = pageUrl
    webPage.isPartOf = { '@id': `${pageUrl}#website` }
  }

  const application = {
    '@type': 'SoftwareApplication',
    name: siteName,
    applicationCategory: 'MultimediaApplication',
    operatingSystem: 'Web',
    description: seoDescription,
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'CNY',
    },
    featureList: [
      '粘贴链接解析视频',
      '选择清晰度下载',
      '手机浏览器保存',
      'AI 摘要、字幕、思维导图和问答',
    ],
  }
  if (pageUrl) application.url = pageUrl
  if (imageUrl) application.image = imageUrl

  const payload = {
    '@context': 'https://schema.org',
    '@graph': [
      website,
      webPage,
      application,
      {
        '@type': 'HowTo',
        name: '在线视频下载步骤',
        description: '粘贴视频链接，选择清晰度后保存到本地，并按需生成 AI 总结。',
        step: steps.map((step, index) => ({
          '@type': 'HowToStep',
          position: index + 1,
          name: step.title,
          text: step.body,
        })),
      },
      {
        '@type': 'FAQPage',
        mainEntity: faqs.map((item) => ({
          '@type': 'Question',
          name: item.question,
          acceptedAnswer: {
            '@type': 'Answer',
            text: item.answer,
          },
        })),
      },
    ],
  }

  return JSON.stringify(payload).replaceAll('<', '\\u003c')
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}
