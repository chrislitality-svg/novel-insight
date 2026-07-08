<template>
  <div class="page reader-shell" :class="`theme-${theme}`" v-loading="loading">
    <div class="bar-header">
      <div>
        <h2 class="page-title">原文阅读</h2>
        <p class="page-subtitle">{{ book?.title ? `《${book.title}》` : '' }}</p>
      </div>
      <el-button @click="$router.push(`/books/${id}`)" plain round size="small">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
    </div>

    <!-- 阅读工具栏:目录 / 字号 / 字体 / 背景 -->
    <div class="reader-toolbar">
      <button class="tb-btn" @click="catalogOpen = !catalogOpen">☰ 目录</button>
      <div class="tb-group">
        <button class="tb-btn" @click="setFont(-1)">A−</button>
        <span class="tb-val">{{ fontSize }}</span>
        <button class="tb-btn" @click="setFont(1)">A＋</button>
      </div>
      <div class="tb-group">
        <button class="tb-btn" :class="{ on: fontFam==='sans' }" @click="fontFam='sans'">默认</button>
        <button class="tb-btn" :class="{ on: fontFam==='song' }" @click="fontFam='song'">宋体</button>
        <button class="tb-btn" :class="{ on: fontFam==='hei' }" @click="fontFam='hei'">黑体</button>
      </div>
      <div class="tb-group themes">
        <button class="th th-light" :class="{ on: theme==='light' }" @click="theme='light'" title="日间"></button>
        <button class="th th-sepia" :class="{ on: theme==='sepia' }" @click="theme='sepia'" title="护眼"></button>
        <button class="th th-dark" :class="{ on: theme==='dark' }" @click="theme='dark'" title="夜间"></button>
      </div>
    </div>

    <div class="reader-main">
      <div v-if="catalogOpen && isMobile" class="catalog-backdrop" @click="catalogOpen = false"></div>

      <!-- 目录(桌面内嵌可收起 / 手机抽屉) -->
      <div class="pane pane-list" :class="{ open: catalogOpen }" v-show="catalogOpen || !isMobile">
        <div class="pane-head">
          <el-input v-model="kw" size="small" placeholder="搜章节" clearable />
        </div>
        <div class="pane-body chapter-list">
          <div v-for="c in filteredChapters" :key="c.id" class="chapter-item clickable"
            :class="{ active: current?.id === c.id }" @click="select(c)">
            <span class="ch-t">{{ c.title }}</span>
          </div>
          <div v-if="filteredChapters.length === 0" class="muted" style="padding:14px">无匹配章节</div>
        </div>
      </div>

      <!-- 阅读区 -->
      <div class="pane pane-read">
        <div class="pane-body read-body" ref="readBody" :style="bodyStyle">
          <template v-if="current">
            <h3 class="read-title" :style="{ color: th.fg }">{{ current.title }}</h3>
            <div class="read-meta" :style="{ color: th.meta }">第 {{ current.index }} 章 · {{ current.char_count }} 字</div>
            <article class="read-content" :style="readStyle">
              <p v-for="(para, i) in paragraphs" :key="i">{{ para }}</p>
            </article>
            <div class="read-nav">
              <el-button :disabled="!prevCh" @click="select(prevCh)" plain round>← 上一章</el-button>
              <span class="muted">{{ curPos }} / {{ chapters.length }}</span>
              <el-button :disabled="!nextCh" @click="select(nextCh)" plain round>下一章 →</el-button>
            </div>
          </template>
          <el-empty v-else description="选择章节开始阅读" :image-size="90" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const id = Number(props.id)
const route = useRoute()

const loading = ref(true)
const book = ref(null)
const chapters = ref([])
const current = ref(null)
const kw = ref('')
const readBody = ref(null)

// 阅读设置(localStorage 持久化)
const fontSize = ref(Number(localStorage.getItem('rd_fs')) || 18)
const fontFam = ref(localStorage.getItem('rd_ff') || 'song')
const theme = ref(localStorage.getItem('rd_th') || 'light')
const isMobile = ref(window.innerWidth <= 900)
const catalogOpen = ref(window.innerWidth > 900)

const FAM = { sans: 'var(--font-body)', song: '"Songti SC","Source Han Serif SC","SimSun",serif', hei: '"PingFang SC","Microsoft YaHei","Hiragino Sans GB",sans-serif' }
const THEME = {
  light: { bg: '#ffffff', fg: '#222222', meta: '#6b6b6b' },
  sepia: { bg: '#f5ecd9', fg: '#5b4636', meta: '#8a7a66' },
  dark: { bg: '#1b1b1d', fg: '#c2c2c4', meta: '#8a8a8e' },
}
const th = computed(() => THEME[theme.value] || THEME.light)
const readStyle = computed(() => ({ fontSize: fontSize.value + 'px', fontFamily: FAM[fontFam.value], lineHeight: 2, color: th.value.fg }))
const bodyStyle = computed(() => ({ background: th.value.bg }))
function setFont(d) { fontSize.value = Math.min(26, Math.max(14, fontSize.value + d)) }

watch(fontSize, (v) => localStorage.setItem('rd_fs', v))
watch(fontFam, (v) => localStorage.setItem('rd_ff', v))
watch(theme, (v) => localStorage.setItem('rd_th', v))

const filteredChapters = computed(() => {
  const k = kw.value.trim()
  return k ? chapters.value.filter((c) => c.title.includes(k)) : chapters.value
})
const paragraphs = computed(() => (current.value?.content || '').split('\n').map((s) => s.trim()).filter(Boolean))
const curIdx = computed(() => chapters.value.findIndex((c) => c.id === current.value?.id))
const curPos = computed(() => (curIdx.value >= 0 ? curIdx.value + 1 : 0))
const prevCh = computed(() => (curIdx.value > 0 ? chapters.value[curIdx.value - 1] : null))
const nextCh = computed(() => (curIdx.value >= 0 && curIdx.value < chapters.value.length - 1 ? chapters.value[curIdx.value + 1] : null))

async function select(c) {
  if (!c) return
  const { data } = await api.getChapter(c.id)
  current.value = { ...c, ...data }
  if (readBody.value) readBody.value.scrollTop = 0
  if (isMobile.value) catalogOpen.value = false
}

function onResize() { isMobile.value = window.innerWidth <= 900 }
onMounted(async () => {
  window.addEventListener('resize', onResize)
  try {
    const [bk, chs] = await Promise.all([api.getBook(id), api.listChapters(id)])
    book.value = bk.data
    chapters.value = chs.data
    // 支持 ?cid=<章节id> 直达某章(从做派卡「读原文」跳来)
    const cid = Number(route.query.cid)
    const target = (cid && chapters.value.find((c) => c.id === cid)) || chapters.value[0]
    if (target) await select(target)
  } catch {
    ElMessage({ message: '加载原文失败,请稍后重试', type: 'error', grouping: true })
  } finally {
    loading.value = false
  }
})
onUnmounted(() => window.removeEventListener('resize', onResize))
</script>

<style scoped>
.reader-shell { height: calc(100vh - 3.5rem); display: flex; flex-direction: column; overflow: hidden; }

/* 工具栏 */
.reader-toolbar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; padding: 8px 2px 12px; border-bottom: 1px solid var(--border); }
.tb-group { display: flex; align-items: center; gap: 4px; }
.tb-btn { border: 1px solid var(--border); background: var(--card); color: var(--fg); border-radius: 6px; padding: 5px 12px; font-size: 13px; cursor: pointer; transition: background-color .12s, border-color .12s, color .12s; }
.tb-btn:hover { border-color: var(--accent); color: var(--accent); }
.tb-btn.on { background: var(--accent); color: #fff; border-color: var(--accent); }
.tb-val { font-size: 13px; color: var(--muted-fg); min-width: 22px; text-align: center; }
.themes { gap: 8px; }
.th { width: 24px; height: 24px; border-radius: 50%; border: 2px solid var(--border); cursor: pointer; }
.th.on { border-color: var(--accent); box-shadow: 0 0 0 2px #fff inset; }
.th-light { background: #ffffff; }
.th-sepia { background: #f5ecd9; }
.th-dark { background: #1b1b1d; }

.reader-main { flex: 1; min-height: 0; display: flex; gap: 16px; margin-top: 12px; position: relative; }
.pane { border: 1px solid var(--border); border-radius: 8px; background: var(--card); display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.pane-list { width: 280px; flex-shrink: 0; }
.pane-read { flex: 1; min-width: 0; }
.pane-head { flex-shrink: 0; padding: 10px 12px; border-bottom: 1px solid var(--border); }
.pane-body { flex: 1; overflow-y: auto; min-height: 0; }
.chapter-item { padding: 9px 14px; border-bottom: 1px solid var(--border); font-size: 13.5px; transition: background-color .12s; }
.chapter-item:hover { background: var(--muted); }
.chapter-item.active { background: var(--accent-subtle); box-shadow: inset 3px 0 0 var(--accent); }
.ch-t { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.read-body { padding: 24px 0; transition: background-color .2s; }
.read-title { font-family: var(--font-display); font-weight: 600; font-size: 1.4rem; text-align: center; max-width: 740px; margin: 0 auto 6px; padding: 0 24px; }
.read-meta { text-align: center; color: var(--muted-fg); font-size: 13px; margin-bottom: 20px; }
.read-content { max-width: 740px; margin: 0 auto; padding: 0 28px; }
.read-content p { margin: 0 0 1.1em; color: inherit; text-align: justify; }
.read-nav { max-width: 740px; margin: 22px auto 0; padding: 18px 28px 0; border-top: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }

/* 夜间模式下让阅读区卡片边框也变深(背景由内联样式控制) */
.theme-dark .pane-read { border-color: #2C2C2E; }
.theme-dark .read-nav { border-color: #2C2C2E; }

/* 手机:目录变抽屉 */
@media (max-width: 900px) {
  .pane-list {
    position: fixed; top: 0; left: 0; bottom: 0; width: 82%; max-width: 320px;
    z-index: 60; border-radius: 0; transform: translateX(-100%); transition: transform .22s ease;
  }
  .pane-list.open { transform: none; }
  .catalog-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.4); z-index: 55; }
  .read-content { padding: 0 18px; }
  .read-title { padding: 0 18px; }
}
</style>
