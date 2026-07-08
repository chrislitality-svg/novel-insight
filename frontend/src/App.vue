<template>
  <el-config-provider :locale="zhCn">
  <el-container style="height:100%">
    <el-header class="topbar">
      <div class="brand clickable" @click="$router.push('/books')">
        <span class="brand-name">Novel Insight</span>
        <span class="brand-sub">人情世故分析</span>
      </div>

      <!-- 全局搜索 + 即时预览下拉 -->
      <div class="search-box" ref="boxRef">
        <div class="search-wrap" :class="{ 'is-open': panelOpen && hasInput }">
          <el-icon class="search-icon"><Search /></el-icon>
          <input
            v-model="searchQuery"
            class="global-search"
            placeholder="搜角色、场景、关键词…"
            role="combobox"
            :aria-expanded="panelOpen"
            aria-controls="search-preview"
            @keydown.enter="doSearch"
            @keydown.down.prevent="move(1)"
            @keydown.up.prevent="move(-1)"
            @keydown.esc="closePanel"
            @focus="onFocus"
          />
          <button v-if="searchQuery" class="search-clear" @click="clearSearch" tabindex="-1" aria-label="清除">×</button>
        </div>

        <div v-if="panelOpen && hasInput" id="search-preview" class="search-preview" role="listbox">
          <div v-if="previewLoading" class="sp-state muted">搜索中…</div>

          <template v-else-if="previewTotal > 0">
            <div v-if="scopeTitle" class="sp-scope">在《{{ scopeTitle }}》内搜索</div>

            <div v-if="previewDialogue.length" class="sp-group">
              <div class="sp-group-head">对话片段</div>
              <button
                v-for="(d, i) in previewDialogue" :key="'d' + d.dialogue_id"
                class="sp-item" :class="{ active: activeIdx === flatIndex('d', i) }"
                role="option" @click="openChapter(d)" @mouseenter="activeIdx = flatIndex('d', i)"
              >
                <span class="sp-chapter">{{ d.chapter_title }}</span>
                <span class="sp-text" v-html="highlight(d.original_text)"></span>
              </button>
            </div>

            <div v-if="previewBehavior.length" class="sp-group">
              <div class="sp-group-head">场景与做派</div>
              <button
                v-for="(b, i) in previewBehavior" :key="'b' + b.behavior_id"
                class="sp-item" :class="{ active: activeIdx === flatIndex('b', i) }"
                role="option" @click="openChapter(b)" @mouseenter="activeIdx = flatIndex('b', i)"
              >
                <span class="sp-chapter">{{ b.chapter_title }}</span>
                <span class="sp-text" v-html="highlight(b.scene_summary)"></span>
              </button>
            </div>

            <button class="sp-all" @click="doSearch">
              查看全部结果 <b>{{ previewTotal }}{{ previewTotal >= CAP ? '+' : '' }}</b> 条 →
            </button>
          </template>

          <div v-else class="sp-state">
            <div class="muted">没有匹配「{{ searchQuery.trim() }}」的结果</div>
            <div class="sp-hint muted">试试更短的关键词，或角色名 / 场景词</div>
          </div>
        </div>
      </div>

      <div class="nav">
        <el-button text :type="isUpload ? 'primary' : ''" @click="$router.push('/upload')" size="small">
          <el-icon><Upload /></el-icon><span class="nav-label">投书</span>
        </el-button>
        <el-button text :type="isBooks ? 'primary' : ''" @click="$router.push('/books')" size="small">
          <el-icon><Files /></el-icon><span class="nav-label">书架</span>
        </el-button>
        <button
          class="theme-toggle clickable"
          @click="toggleTheme"
          :title="isDark ? '切换浅色模式' : '切换深色模式'"
          :aria-label="isDark ? '切换浅色模式' : '切换深色模式'"
        >
          <el-icon v-if="isDark"><Sunny /></el-icon>
          <el-icon v-else><Moon /></el-icon>
        </button>
      </div>
    </el-header>
    <el-main style="padding:0">
      <router-view v-slot="{ Component }">
        <keep-alive :include="['BookList']"><component :is="Component" /></keep-alive>
      </router-view>
    </el-main>
  </el-container>
  </el-config-provider>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Upload, Files, Moon, Sunny, Search } from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { api } from './api'

const route = useRoute()
const router = useRouter()
const isUpload = computed(() => route.path === '/upload')
const isBooks = computed(() => route.path === '/books')

// ===== 全局搜索 + 即时预览 =====
const CAP = 8 // 每类预览上限相关：后端通常截断，>= 时显示 “+”
const searchQuery = ref('')
const boxRef = ref(null)
const panelOpen = ref(false)
const previewLoading = ref(false)
const previewDialogue = ref([])
const previewBehavior = ref([])
const previewTotal = ref(0)
const scopeTitle = ref('')
const activeIdx = ref(-1)
let debounceTimer = null

const hasInput = computed(() => searchQuery.value.trim().length >= 2)
const flatList = computed(() => [...previewDialogue.value, ...previewBehavior.value])
function flatIndex(kind, i) { return kind === 'd' ? i : previewDialogue.value.length + i }

function currentBookId() {
  const m = route.path.match(/^\/books\/(\d+)/)
  return m ? Number(m[1]) : null
}

function escapeHtml(s) {
  return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
}
function highlight(text) {
  const t = escapeHtml(text)
  const q = searchQuery.value.trim()
  if (!q) return t
  const safe = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return t.replace(new RegExp(safe, 'gi'), (m) => `<mark>${m}</mark>`)
}

// 输入即搜（防抖 250ms），仅在 >= 2 字时触发，避免抖动与无意义请求
watch(searchQuery, (v) => {
  clearTimeout(debounceTimer)
  activeIdx.value = -1
  const q = v.trim()
  if (q.length < 2) { panelOpen.value = false; return }
  debounceTimer = setTimeout(() => fetchPreview(q), 250)
})

async function fetchPreview(q) {
  if (searchQuery.value.trim() !== q) return // 已被更新，丢弃
  panelOpen.value = true
  previewLoading.value = true
  try {
    const bid = currentBookId()
    const { data } = await api.search(q, bid)
    if (searchQuery.value.trim() !== q) return // 竞态：晚到的旧响应丢弃
    previewDialogue.value = (data.dialogue || []).slice(0, 4)
    previewBehavior.value = (data.behavior || []).slice(0, 4)
    previewTotal.value = (data.dialogue?.length || 0) + (data.behavior?.length || 0)
    scopeTitle.value = ''
  } finally {
    previewLoading.value = false
  }
}

function onFocus() { if (hasInput.value && previewTotal.value >= 0) panelOpen.value = true }
function closePanel() { panelOpen.value = false; activeIdx.value = -1 }
function clearSearch() { searchQuery.value = ''; closePanel() }

function move(dir) {
  if (!panelOpen.value || !flatList.value.length) return
  const n = flatList.value.length
  activeIdx.value = (activeIdx.value + dir + n) % n
}

function openChapter(item) {
  closePanel()
  router.push({ path: `/books/${item.book_id}/read`, query: { cid: item.chapter_id } })
}

function doSearch() {
  // 高亮项优先：方向键选中后回车直达该条
  if (activeIdx.value >= 0 && flatList.value[activeIdx.value]) {
    return openChapter(flatList.value[activeIdx.value])
  }
  const q = searchQuery.value.trim()
  if (!q) return
  closePanel()
  const bookId = currentBookId()
  router.push({ path: '/search', query: bookId ? { q, book_id: bookId } : { q } })
}

// 点击外部关闭下拉
function onDocClick(e) { if (boxRef.value && !boxRef.value.contains(e.target)) closePanel() }
onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => { document.removeEventListener('click', onDocClick); clearTimeout(debounceTimer) })

// URL 同步：从地址栏进入 /search?q=xxx 时回填
watch(() => route.query.q, (v) => { if (route.path === '/search') searchQuery.value = String(v || '') }, { immediate: true })
// 路由切换时关闭预览
watch(() => route.path, closePanel)

// ===== 主题切换 =====
const isDark = ref(localStorage.getItem('ni-theme') === 'dark')
document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
function toggleTheme() {
  isDark.value = !isDark.value
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
  localStorage.setItem('ni-theme', isDark.value ? 'dark' : 'light')
}
</script>

<style scoped>
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--card); border-bottom: 1px solid var(--border);
  height: 3rem; padding: 0 var(--s-xl);
}
.brand { display: flex; align-items: baseline; gap: .625rem; }
.brand-name {
  font-family: var(--font-display); font-size: 1.125rem; font-weight: 600;
  color: var(--fg); letter-spacing: -.01em; white-space: nowrap;
}
.brand-sub {
  font-family: var(--font-mono); font-size: .625rem; letter-spacing: .08em;
  text-transform: uppercase; color: var(--muted-fg);
}

/* 搜索盒：相对定位容器，承载下拉 */
.search-box { flex: 1; min-width: 0; max-width: 420px; margin: 0 24px; position: relative; }
.search-wrap {
  display: flex; align-items: center; gap: 6px;
  background: var(--muted); border: 1px solid var(--border); border-radius: 999px;
  padding: 5px 12px;
  transition: border-color .15s, background-color .15s, border-radius .15s;
}
.search-wrap:focus-within { border-color: var(--accent); background: var(--card); }
.search-wrap.is-open { border-radius: 18px 18px 0 0; border-bottom-color: transparent; }
.search-icon { color: var(--muted-fg); font-size: 14px; flex-shrink: 0; }
.global-search {
  flex: 1; min-width: 0; border: none; outline: none; background: transparent;
  font-size: 13px; color: var(--fg); font-family: inherit;
}
.global-search::placeholder { color: var(--muted-fg); }
.search-clear {
  border: none; background: none; cursor: pointer; color: var(--muted-fg);
  font-size: 18px; line-height: 1; padding: 0 4px;
}
.search-clear:hover { color: var(--fg); }

/* 即时预览下拉 */
.search-preview {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 50;
  background: var(--card); border: 1px solid var(--accent);
  border-top: 1px solid var(--border);
  border-radius: 0 0 14px 14px; padding: 6px;
  max-height: 70vh; overflow-y: auto;
  box-shadow: 0 12px 28px rgba(0, 0, 0, .10);
}
.sp-state { padding: 16px 12px; text-align: center; }
.sp-hint { font-size: 12px; margin-top: 4px; }
.sp-scope {
  font-family: var(--font-mono); font-size: 11px; color: var(--accent);
  padding: 4px 10px 6px;
}
.sp-group { margin-bottom: 2px; }
.sp-group-head {
  font-family: var(--font-mono); font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; color: var(--muted-fg); padding: 6px 10px 3px;
}
.sp-item {
  display: block; width: 100%; text-align: left;
  border: none; background: none; cursor: pointer;
  padding: 7px 10px; border-radius: 8px; line-height: 1.45;
  transition: background-color .1s;
}
.sp-item.active, .sp-item:hover { background: var(--accent-subtle); }
.sp-chapter {
  display: block; font-size: 11px; color: var(--muted-fg);
  font-family: var(--font-mono); margin-bottom: 1px;
}
.sp-text {
  display: block; font-size: 13px; color: var(--fg);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.sp-text :deep(mark) { background: #ffe48a; color: inherit; padding: 0 1px; border-radius: 2px; }
[data-theme="dark"] .sp-text :deep(mark) { background: #5a4a1a; color: #f0e0a0; }
.sp-all {
  display: block; width: 100%; text-align: center; cursor: pointer;
  border: none; border-top: 1px solid var(--border); margin-top: 4px;
  background: none; color: var(--accent); font-size: 12.5px; font-weight: 600;
  padding: 9px; border-radius: 0 0 10px 10px;
}
.sp-all:hover { background: var(--accent-subtle); }

.nav { display: flex; align-items: center; gap: .125rem; flex-shrink: 0; }
@media (max-width: 640px) {
  .topbar { padding: 0 12px; }
  .brand-sub { display: none; }
  .brand-name { font-size: 1rem; }
  .search-box { margin: 0 10px; max-width: none; }
}
/* 手机:导航按钮仅留图标,给搜索框让出空间,避免顶栏溢出 */
@media (max-width: 480px) {
  .topbar { padding: 0 10px; }
  .search-box { margin: 0 8px; }
  .nav-label { display: none; }
}
.theme-toggle {
  display: inline-flex; align-items: center; justify-content: center;
  width: 2rem; height: 2rem; margin-left: .5rem; padding: 0;
  border: 1px solid var(--border); border-radius: 999px;
  background: var(--card); color: var(--fg);
  transition: border-color .15s, color .15s, background-color .15s, transform .25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.theme-toggle:hover { border-color: var(--accent); color: var(--accent); transform: rotate(-18deg); }
.theme-toggle .el-icon { font-size: 1rem; }
</style>
