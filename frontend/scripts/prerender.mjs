import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createServer, loadEnv } from 'vite'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const envFromFile = loadEnv('production', root, '')
if (!process.env.VITE_SITE_URL && envFromFile.VITE_SITE_URL) {
  process.env.VITE_SITE_URL = envFromFile.VITE_SITE_URL
}

const { getSiteUrl, renderLlmsTxt, renderRobotsTxt, renderSitemap } = await import('../seo.config.mjs')

const vite = await createServer({
  root,
  configFile: path.join(root, 'vite.config.js'),
  server: { middlewareMode: true },
  appType: 'custom',
  logLevel: 'error',
})

try {
  const { render } = await vite.ssrLoadModule('/src/entry-server.js')
  const appHtml = await render()
  const h1Count = appHtml.match(/<h1[\s>]/g)?.length || 0
  if (h1Count !== 1) {
    throw new Error(`预渲染页面应只有 1 个 h1，当前为 ${h1Count} 个`)
  }
  if (!appHtml.includes('在线视频下载步骤') || !appHtml.includes('视频下载常见问题')) {
    throw new Error('预渲染结果缺少下载步骤或常见问题')
  }
  if (!appHtml.includes('id="product-definition"')) {
    throw new Error('预渲染结果缺少可供 AI 引用的产品说明')
  }

  const indexPath = path.join(root, 'dist', 'index.html')
  const html = fs.readFileSync(indexPath, 'utf8')
  const mount = '<div id="app"></div>'
  if (!html.includes(mount)) {
    throw new Error('dist/index.html 中找不到 <div id="app"></div>')
  }
  if (html.includes('<!--seo:head-->')) {
    throw new Error('SEO 标签没有写入 dist/index.html')
  }

  fs.writeFileSync(indexPath, html.replace(mount, `<div id="app">${appHtml}</div>`))

  const siteUrl = getSiteUrl()
  fs.writeFileSync(path.join(root, 'dist', 'robots.txt'), renderRobotsTxt(siteUrl))
  fs.writeFileSync(path.join(root, 'dist', 'sitemap.xml'), renderSitemap(siteUrl))
  fs.writeFileSync(path.join(root, 'dist', 'llms.txt'), renderLlmsTxt(siteUrl))

  if (siteUrl) {
    console.log(`SEO 预渲染完成，站点地址：${siteUrl}`)
  } else {
    console.warn(
      'SEO 预渲染完成。尚未设置 VITE_SITE_URL，canonical、og:url、og:image 和 sitemap 绝对地址会在填写域名并重新构建后生成。',
    )
  }
} finally {
  await vite.close()
}
