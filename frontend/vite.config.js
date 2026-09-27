import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { renderLlmsTxt, renderSeoHead } from './seo.config.mjs'

function seoHeadPlugin() {
  return {
    name: 'seo-head',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = req.url?.split('?')[0]
        if (pathname !== '/llms.txt') {
          next()
          return
        }
        res.statusCode = 200
        res.setHeader('Content-Type', 'text/plain; charset=utf-8')
        res.end(renderLlmsTxt())
      })
    },
    transformIndexHtml(html) {
      if (!html.includes('<!--seo:head-->')) {
        throw new Error('index.html 缺少 <!--seo:head-->')
      }
      return html.replace('<!--seo:head-->', renderSeoHead())
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  if (!process.env.VITE_SITE_URL && env.VITE_SITE_URL) {
    process.env.VITE_SITE_URL = env.VITE_SITE_URL
  }

  return {
    plugins: [vue(), seoHeadPlugin()],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
