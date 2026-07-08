<template>
  <div class="page search-page" v-loading="loading">
    <div class="bar-header">
      <div>
        <h2 class="page-title">搜索结果</h2>
        <p class="page-subtitle" v-if="q">
          关键词「{{ q }}」<span v-if="bookTitle">· 在《{{ bookTitle }}》内</span>
          <el-button v-if="bookId" text size="small" @click="clearBookFilter" style="margin-left:8px">搜索全部书籍</el-button>
        </p>
      </div>
      <el-button @click="$router.go(-1)" plain round size="small">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
    </div>

    <el-empty v-if="!loading && !q" description="在顶部搜索框输入关键词后回车" />

    <template v-else-if="!loading">
      <div v-if="totalResults === 0">
        <el-empty :description="`「${q}」没有匹配结果`" />
      </div>
      <template v-else>
        <!-- 角色结果（仅当书内搜索） -->
        <section v-if="characters.length" class="result-section">
          <div class="section-head">
            <span class="section-name">角色</span>
            <span class="section-count">{{ characters.length }} 个</span>
          </div>
          <div class="char-grid">
            <button v-for="c in characters" :key="c.id" class="char-card" @click="openCharacter(c)">
              <span class="char-name">{{ c.name }}</span>
              <span class="char-meta" v-if="c.appearance_count">{{ c.appearance_count }} 次出场</span>
            </button>
          </div>
        </section>

        <!-- 对话结果 -->
        <section v-if="dialogue.length" class="result-section">
          <div class="section-head">
            <span class="section-name">对话片段</span>
            <span class="section-count">{{ dialogue.length }} 条</span>
          </div>
          <div class="result-list">
            <button v-for="d in dialogue" :key="d.dialogue_id" class="result-card" @click="openChapter(d.book_id, d.chapter_id)">
              <div class="rc-head">
                <span class="rc-chapter">{{ d.chapter_title }}</span>
                <span class="rc-speaker" v-if="d.speaker">{{ d.speaker }}<span v-if="d.listener"> → {{ d.listener }}</span></span>
              </div>
              <div class="rc-quote" v-html="highlight(d.original_text)"></div>
              <div class="rc-foot" v-if="d.lesson">{{ d.lesson }}</div>
            </button>
          </div>
        </section>

        <!-- 做派/场景结果 -->
        <section v-if="behavior.length" class="result-section">
          <div class="section-head">
            <span class="section-name">场景与做派</span>
            <span class="section-count">{{ behavior.length }} 条</span>
          </div>
          <div class="result-list">
            <button v-for="b in behavior" :key="b.behavior_id" class="result-card" @click="openChapter(b.book_id, b.chapter_id)">
              <div class="rc-head">
                <span class="rc-chapter">{{ b.chapter_title }}</span>
              </div>
              <div class="rc-scene" v-html="highlight(b.scene_summary)"></div>
              <div class="rc-foot" v-if="b.core_lesson" v-html="highlight(b.core_lesson)"></div>
            </button>
          </div>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const behavior = ref([])
const dialogue = ref([])
const characters = ref([])
const bookTitle = ref('')

const q = computed(() => String(route.query.q || '').trim())
const bookId = computed(() => {
  const v = route.query.book_id
  return v ? Number(v) : null
})
const totalResults = computed(() => behavior.value.length + dialogue.value.length + characters.value.length)

function escapeHtml(s) {
  return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
}
function highlight(text) {
  const t = escapeHtml(text)
  if (!q.value) return t
  const safe = q.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return t.replace(new RegExp(safe, 'gi'), (m) => `<mark>${m}</mark>`)
}

async function runSearch() {
  if (!q.value) {
    behavior.value = []; dialogue.value = []; characters.value = []; bookTitle.value = ''
    return
  }
  loading.value = true
  try {
    const calls = [api.search(q.value, bookId.value)]
    if (bookId.value) {
      calls.push(api.getBook(bookId.value).catch(() => null))
      calls.push(api.listCharacters(bookId.value).catch(() => null))
    }
    const [searchRes, bookRes, charsRes] = await Promise.all(calls)
    behavior.value = searchRes.data.behavior || []
    dialogue.value = searchRes.data.dialogue || []
    bookTitle.value = bookRes?.data?.title || ''
    if (charsRes?.data) {
      const lower = q.value.toLowerCase()
      characters.value = (charsRes.data || []).filter(c => (c.name || '').toLowerCase().includes(lower))
    } else {
      characters.value = []
    }
  } catch {
    ElMessage({ message: '搜索失败,请稍后重试', type: 'error', grouping: true })
  } finally {
    loading.value = false
  }
}

function openChapter(bid, cid) {
  router.push({ path: `/books/${bid}/read`, query: { cid } })
}
function openCharacter(c) {
  if (bookId.value) router.push(`/books/${bookId.value}/characters/${c.id}`)
}
function clearBookFilter() {
  router.replace({ path: '/search', query: { q: q.value } })
}

watch(() => [route.query.q, route.query.book_id], runSearch)
onMounted(runSearch)
</script>

<style scoped>
.search-page { max-width: 960px; margin: 0 auto; }

.result-section { margin-bottom: 28px; }
.section-head {
  display: flex; align-items: baseline; gap: 8px; margin-bottom: 12px;
  padding-bottom: 8px; border-bottom: 1px solid var(--border);
}
.section-name { font-family: var(--font-display); font-size: 16px; font-weight: 600; color: var(--fg); }
.section-count { font-size: 12px; color: var(--muted-fg); }

/* 角色卡 */
.char-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.char-card {
  border: 1px solid var(--border); background: var(--card); color: var(--fg);
  padding: 8px 14px; border-radius: 999px; cursor: pointer;
  display: flex; align-items: center; gap: 8px;
  transition: border-color .12s, background-color .12s;
}
.char-card:hover { border-color: var(--accent); background: var(--accent-subtle); }
.char-name { font-size: 14px; font-weight: 600; }
.char-meta { font-size: 12px; color: var(--muted-fg); }

/* 结果卡 */
.result-list { display: flex; flex-direction: column; gap: 10px; }
.result-card {
  text-align: left; width: 100%;
  border: 1px solid var(--border); border-left: 3px solid var(--accent);
  background: var(--card); padding: 14px 18px; border-radius: 6px;
  cursor: pointer; transition: background-color .12s, border-color .12s;
  display: block;
}
.result-card:hover { background: var(--accent-subtle); border-color: var(--accent-secondary, var(--accent)); }
.rc-head { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 6px; font-size: 12.5px; color: var(--muted-fg); }
.rc-chapter { font-weight: 600; color: var(--fg); }
.rc-speaker { font-family: var(--font-mono); }
.rc-quote { font-size: 14px; line-height: 1.7; color: var(--fg); padding: 4px 0; }
.rc-scene { font-size: 14px; line-height: 1.7; color: var(--fg); }
.rc-foot { margin-top: 6px; font-size: 13px; color: var(--muted-fg); line-height: 1.6; }
.result-card :deep(mark) { background: #ffe48a; color: inherit; padding: 0 2px; border-radius: 2px; }
[data-theme="dark"] .result-card :deep(mark) { background: #5a4a1a; color: #f0e0a0; }
</style>
