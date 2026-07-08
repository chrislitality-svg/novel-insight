import { createApp } from 'vue'
// 组件按需由 unplugin 注入(见 vite.config.js);此处只保留全量样式表
// ——它体积远小于全量组件 JS,且保证 ElMessage 等程序化组件不缺样式。
import 'element-plus/dist/index.css'
import * as Icons from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)
for (const [name, comp] of Object.entries(Icons)) {
  app.component(name, comp)
}
app.use(router)
app.mount('#app')
