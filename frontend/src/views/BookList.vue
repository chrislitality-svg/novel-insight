<template>
  <div class="page booklist">
    <!-- 英雄区 -->
    <header class="hero">
      <div class="hero-main">
        <div class="hero-kicker">NOVEL INSIGHT · 人情世故拆书馆</div>
        <h1 class="hero-title">把网文里的处世智慧，拆成能用的卡片</h1>
        <p class="hero-sub">官场进阶 · 话术博弈 · 潜规则 —— 逐章拆解成「做派卡 · 对话卡 · 规则手册」，可迁移到现实。</p>
      </div>
      <div class="hero-actions">
        <el-button v-if="books.length >= 2" round size="large" @click="$router.push('/compare')">
          <el-icon><Switch /></el-icon> 两书对比
        </el-button>
        <el-button type="primary" round size="large" @click="$router.push('/upload')">
          <el-icon><Plus /></el-icon> 投新书
        </el-button>
      </div>
    </header>

    <div class="hero-banner">
      <img src="/gen/hero.jpg" alt="" loading="lazy" />
    </div>

    <el-empty v-if="!loading && books.length === 0" description="还没有书，去投一本吧" />

    <!-- 书卡（紧跟 hero 之后，第一眼就能看到） -->
    <div class="book-grid" v-loading="loading">
      <article v-for="b in books" :key="b.id" class="bcard">
        <div class="bcard-top clickable" @click="open(b.id)">
          <div class="cover" :class="{ 'has-img': coverFor(b) }">
            <img v-if="coverFor(b)" :src="coverFor(b)" alt="" loading="lazy" />
            <span v-else>{{ b.title.slice(0, 1) }}</span>
          </div>
          <div class="bcard-meta">
            <h3 class="bcard-title" :title="b.title">{{ b.title }}</h3>
            <div class="bcard-sub">
              <span v-if="b.protagonist">主角 · {{ b.protagonist }}</span>
              <span v-else>{{ b.author || '佚名' }}</span>
              <span v-if="b.setting"> · {{ b.setting }}</span>
            </div>
            <el-tag :type="statusType(b.status)" size="small" effect="plain" round>{{ statusLabel(b.status) }}</el-tag>
          </div>
        </div>

        <div class="bcard-prog">
          <div class="prog-label">已分析 <b>{{ b.analyzed_chapters }}</b> / {{ b.total_chapters }} 章</div>
          <el-progress :percentage="pct(b)" :show-text="false" :stroke-width="6" />
        </div>

        <div class="bcard-links">
          <button @click="go(b.id, 'behavior-cards')">做派卡</button>
          <button @click="go(b.id, 'dialogue-cards')">对话卡</button>
          <button @click="go(b.id, 'rules')">规则手册</button>
          <button @click="go(b.id, 'family')">家庭</button>
          <button @click="go(b.id, 'read')">读原文</button>
          <button @click="go(b.id, 'stats')">量化</button>
        </div>

        <div class="bcard-foot">
          <button class="enter" @click="open(b.id)">进入拆解 →</button>
          <button class="del" @click="del(b)">删除</button>
        </div>
      </article>
    </div>

  </div>
</template>

<script setup>
import { ref, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

defineOptions({ name: 'BookList' })
const router = useRouter()
const books = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await api.listBooks()
    books.value = data // listBooks 已联查返回主角/背景,无需再逐本请求
  } catch {
    // 后端不可达时只提示一次(grouping 合并重复),保持书架为空,不抛出未处理 rejection
    ElMessage({ message: '加载书架失败,请稍后重试', type: 'error', grouping: true })
  } finally {
    loading.value = false
  }
}
// kept-alive 组件的 onActivated 首次挂载也会触发,既覆盖首屏又覆盖返回刷新,
// 故只用它即可,避免首屏 onMounted+onActivated 双发同一请求
onActivated(load)

// 已生成封面的书(按 id 映射到 /public/gen/);其它书回退字母块
const COVERS = { 1: '/gen/cover-book1.jpg', 2: '/gen/cover-book2.jpg' }
function coverFor(b) { return COVERS[b.id] || null }

function pct(b) { return b.total_chapters ? Math.round((b.analyzed_chapters / b.total_chapters) * 100) : 0 }
function statusType(s) { return { uploaded: 'info', analyzing: 'warning', completed: 'success', failed: 'danger' }[s] || 'info' }
function statusLabel(s) { return { uploaded: '待分析', analyzing: '分析中', completed: '已完成', failed: '失败' }[s] || s }
function open(id) { router.push(`/books/${id}`) }
function go(id, sub) { router.push(`/books/${id}/${sub}`) }

async function del(b) {
  try {
    await ElMessageBox.confirm(`确定删除《${b.title}》及其所有分析结果?`, '删除确认', { type: 'warning' })
    await api.deleteBook(b.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.booklist { max-width: 1360px; }

/* 英雄区 */
.hero {
  display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; flex-wrap: wrap;
  padding: 8px 0 22px; border-bottom: 2px solid var(--accent); margin-bottom: 0;
}
.hero-kicker { font-family: var(--font-mono); font-size: .72rem; letter-spacing: .18em; color: var(--accent); margin-bottom: 10px; }
.hero-title { font-family: var(--font-display); font-weight: 600; font-size: 2.1rem; line-height: 1.2; color: var(--fg); margin: 0 0 10px; max-width: 22ch; }
.hero-sub { color: var(--muted-fg); font-size: .95rem; line-height: 1.7; max-width: 60ch; margin: 0; }
.hero-actions { display: flex; gap: 10px; flex-shrink: 0; }

/* 英雄横幅图 */
.hero-banner { margin-top: 18px; border-radius: 12px; overflow: hidden; border: 1px solid var(--border); line-height: 0; }
.hero-banner img { width: 100%; height: 200px; object-fit: cover; display: block; }
@media (max-width: 768px) { .hero-banner img { height: 130px; } }

/* 书卡 */
.book-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px; margin-top: 24px; }
.bcard {
  min-width: 0;
  border: 1px solid var(--border); border-top: 3px solid var(--accent); border-radius: 10px;
  background: var(--card); padding: 18px; display: flex; flex-direction: column; gap: 14px;
  transition: border-color .15s ease;
}
.bcard:hover { border-color: var(--accent-secondary); }
.bcard-top { display: flex; gap: 14px; align-items: flex-start; min-width: 0; }
.cover {
  width: 52px; height: 68px; flex-shrink: 0; border-radius: 6px; background: var(--accent);
  color: #fff; font-family: var(--font-display); font-size: 30px; font-weight: 600;
  display: flex; align-items: center; justify-content: center; overflow: hidden;
}
.cover.has-img { background: none; width: 62px; height: 88px; }
.cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.bcard-meta { min-width: 0; }
.bcard-title { font-family: var(--font-display); font-weight: 600; font-size: 1.05rem; margin: 0 0 4px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bcard-sub { font-size: 13px; color: var(--muted-fg); margin-bottom: 8px; }

.prog-label { font-size: 12.5px; color: var(--muted-fg); margin-bottom: 6px; }
.prog-label b { color: var(--fg); }

.bcard-links { display: flex; flex-wrap: wrap; gap: 6px; }
.bcard-links button {
  border: 1px solid var(--border); background: var(--muted); color: var(--fg);
  font-size: 12.5px; padding: 5px 11px; border-radius: 999px; cursor: pointer;
  transition: background-color .12s ease, border-color .12s ease, color .12s ease;
}
.bcard-links button:hover { background: var(--accent-subtle); border-color: var(--accent); color: var(--accent); }

.bcard-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 2px; }
.enter { border: none; background: none; color: var(--accent); font-weight: 600; font-size: 13.5px; cursor: pointer; padding: 0; }
.enter:hover { color: var(--accent-secondary); }
.del { border: none; background: none; color: var(--danger); font-size: 12.5px; cursor: pointer; padding: 0; opacity: .8; }
.del:hover { opacity: 1; }

@media (max-width: 768px) {
  .hero-title { font-size: 1.6rem; }
  .book-grid { grid-template-columns: 1fr; }
  .hero-actions { width: 100%; }
}
</style>
