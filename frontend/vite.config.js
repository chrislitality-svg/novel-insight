import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// 开发时把 /api 与 /ws 代理到后端 :8000
export default defineConfig({
  plugins: [
    vue(),
    // 按需引入 Element Plus 组件与 ElMessage 等 API，瘦身首屏 JS。
    // importStyle:false —— 样式仍由 main.js 全量引入 dist/index.css 提供,
    // 既避免 sass 依赖,也杜绝 ElMessage 等程序化组件缺样式的经典坑。
    AutoImport({ resolvers: [ElementPlusResolver({ importStyle: false })] }),
    Components({ resolvers: [ElementPlusResolver({ importStyle: false })] }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
    },
  },
  build: {
    // 构建产物输出到 frontend/dist,后端 main.py 会自动挂载
    outDir: 'dist',
  },
})
