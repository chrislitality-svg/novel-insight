<template>
  <div class="page detail-shell" v-loading="loading">
    <div v-if="book" class="detail-inner">

      <!-- ===== 顶部:标题 + 操作 + 紧凑进度 + 可折叠章节地图 ===== -->
      <div class="detail-top">
        <div class="head">
          <div>
            <h2 class="page-title" style="margin:0">《{{ book.title }}》</h2>
            <div class="muted">
              {{ book.author || '佚名' }} &middot;
              主角:{{ book.protagonist || '未识别' }}
              <span v-if="book.setting">&middot; {{ book.setting }}</span>
              &middot; 共 {{ book.total_chapters }} 章，待分析 {{ book.analyzable_chapters }} 章
            </div>
          </div>
          <div class="actions">
            <div class="nav-tiles">
              <button class="nav-tile" @click="goto('read')"><el-icon><Reading /></el-icon><span>读原文</span></button>
              <button class="nav-tile" @click="goto('behavior-cards')"><el-icon><Postcard /></el-icon><span>做派卡</span></button>
              <button class="nav-tile" @click="goto('dialogue-cards')"><el-icon><ChatLineSquare /></el-icon><span>对话卡</span></button>
              <button class="nav-tile" @click="goto('rules')"><el-icon><Guide /></el-icon><span>规则手册</span></button>
              <button class="nav-tile" @click="goto('family')"><el-icon><House /></el-icon><span>家庭</span></button>
              <button class="nav-tile" @click="goto('stats')"><el-icon><Histogram /></el-icon><span>量化</span></button>
              <button class="nav-tile" @click="goto('characters')"><el-icon><User /></el-icon><span>人物</span></button>
              <button class="nav-tile" @click="goto('clusters')"><el-icon><Collection /></el-icon><span>情境</span></button>
              <button class="nav-tile nav-tile-ghost" @click="exportMd"><el-icon><Download /></el-icon><span>导出</span></button>
            </div>
          </div>
        </div>

        <!-- 紧凑进度行(单行) -->
        <div class="prog-compact">
          <el-progress :percentage="progPct" :status="progStatus" :stroke-width="8" style="flex:1" />
          <div class="prog-stats-inline">
            <span class="stat-item"><i class="stat-dot done"></i>已完成 <b>{{ progress.analyzed }}</b></span>
            <span class="stat-item" v-if="progress.pending"><i class="stat-dot pending-icon"></i>待分析 <b>{{ progress.pending }}</b></span>
            <span class="stat-item" v-if="progress.failed"><i class="stat-dot failed"></i>失败 <b>{{ progress.failed }}</b></span>
            <span class="stat-item" v-if="running"><i class="stat-dot running-icon"></i>~{{ speed }} 章/分</span>
            <span class="stat-item" v-if="running && eta"><el-icon><Clock /></el-icon> 剩 {{ eta }}</span>
          </div>
          <div class="prog-ctrl">
            <el-button v-if="!running && book.status !== 'completed'" type="primary" round size="small" @click="analyze">
              {{ progress.analyzed > 0 ? '继续分析' : '启动分析' }}
            </el-button>
            <el-button v-if="running" type="warning" round size="small" @click="stop">中止</el-button>
            <el-button v-if="book.status === 'completed'" type="primary" plain round size="small" @click="analyze">重跑失败章</el-button>
            <el-button text size="small" @click="heatmapOpen = !heatmapOpen">
              章节地图 {{ heatmapOpen ? '▴' : '▾' }}
            </el-button>
          </div>
        </div>
        <div v-if="running && progress.current_chapter" class="current-chap">
          <el-icon><Loading /></el-icon> 正在分析：{{ progress.current_chapter }}
        </div>

        <!-- 可折叠:章节完成度地图 -->
        <div class="ch-grid-wrap" v-show="heatmapOpen && chapters.length">
          <div class="ch-grid-title">
            <span class="ch-legend">
              <span class="ch-legend-item"><i class="ch-legend-dot c-success"></i>已完成</span>
              <span class="ch-legend-item"><i class="ch-legend-dot c-running"></i>分析中</span>
              <span class="ch-legend-item"><i class="ch-legend-dot c-pending"></i>待分析</span>
              <span class="ch-legend-item" v-if="progress.failed"><i class="ch-legend-dot c-failed"></i>失败</span>
              <span class="ch-legend-item"><i class="ch-legend-dot c-skip"></i>跳过</span>
            </span>
          </div>
          <div class="ch-grid">
            <el-tooltip
              v-for="c in chapters"
              :key="c.id"
              :content="`${c.title}（${statusLabel(c.analysis_status)}）`"
              placement="top"
              :show-after="300"
            >
              <span class="ch-cell" :class="chCellClass(c)" @click="selectChapter(c)" />
            </el-tooltip>
          </div>
        </div>
      </div>

      <!-- ===== 主体:章节列表 | 详情(各自框内滚动,整页不外滚)===== -->
      <div class="detail-main">
        <div class="pane pane-list">
          <div class="pane-head">
            <b>章节列表</b>
            <span class="muted" style="font-size:12px">（灰色为低密度跳过）</span>
          </div>
          <div class="pane-body chapter-list">
            <div
              v-for="c in chapters"
              :key="c.id"
              class="chapter-item clickable"
              :class="{ active: selected?.id === c.id, skip: !c.should_analyze }"
              @click="selectChapter(c)"
            >
              <span class="ch-title">{{ c.title }}</span>
              <el-tag size="small" :type="statusTag(c.analysis_status)" effect="plain" round>
                {{ densityShort(c) }}
              </el-tag>
            </div>
          </div>
        </div>

        <div class="pane pane-detail">
          <div class="pane-body detail-body">
            <!-- 默认：该书亮点面板（量化 + TOP 技巧/规则 + 精选核心道理） -->
            <div v-if="!selected" class="highlight-panel" v-loading="highlightLoading">
              <div class="hl-header">
                <div>
                  <div class="hl-title">本书亮点</div>
                  <div class="hl-sub">基于 {{ highlight.behaviors || 0 }} 个做派、{{ highlight.dialogues || 0 }} 个对话、{{ highlight.rules || 0 }} 条规则的提炼</div>
                </div>
                <el-button text size="small" @click="goto('stats')" class="hl-more">查看完整量化分析 →</el-button>
              </div>

              <!-- 三个 KPI -->
              <div class="hl-kpis" v-if="highlight.behaviors">
                <div class="hl-kpi"><div class="kn">{{ highlight.behaviors }}</div><div class="kl">做派样本</div></div>
                <div class="hl-kpi"><div class="kn">{{ highlight.dialogues }}</div><div class="kl">对话样本</div></div>
                <div class="hl-kpi"><div class="kn">{{ highlight.rules }}</div><div class="kl">提炼规则</div></div>
              </div>

              <!-- 两栏：TOP 技巧 + TOP 规则领域 -->
              <div class="hl-twocol" v-if="highlight.techniques.length || highlight.rule_categories.length">
                <div class="hl-col" v-if="highlight.techniques.length">
                  <div class="hl-col-title">最常用话术 TOP 5</div>
                  <div class="hl-bar-list">
                    <div v-for="(t, i) in highlight.techniques" :key="t[0]" class="hl-bar-row" @click="goto('dialogue-cards')">
                      <span class="hl-rank">{{ i + 1 }}</span>
                      <span class="hl-bar-label">{{ t[0] }}</span>
                      <div class="hl-bar-track"><div class="hl-bar-fill" :style="{ width: Math.round(t[1] / highlight.techMax * 100) + '%' }" /></div>
                      <span class="hl-bar-val">{{ t[1] }}</span>
                    </div>
                  </div>
                </div>
                <div class="hl-col" v-if="highlight.rule_categories.length">
                  <div class="hl-col-title">规则集中领域 TOP 5</div>
                  <div class="hl-bar-list">
                    <div v-for="(r, i) in highlight.rule_categories" :key="r[0]" class="hl-bar-row" @click="goto('rules')">
                      <span class="hl-rank">{{ i + 1 }}</span>
                      <span class="hl-bar-label">{{ r[0] }}</span>
                      <div class="hl-bar-track"><div class="hl-bar-fill" :style="{ width: Math.round(r[1] / highlight.ruleMax * 100) + '%' }" /></div>
                      <span class="hl-bar-val">{{ r[1] }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 精选核心道理 -->
              <div class="hl-lessons" v-if="highlight.lessons.length">
                <div class="hl-col-title">精选核心道理</div>
                <div class="hl-lesson-list">
                  <div v-for="(l, i) in highlight.lessons" :key="i" class="hl-lesson-item" @click="goto('behavior-cards')">
                    <span class="hl-quote-mark">"</span>
                    <span class="hl-lesson-text">{{ l.text }}</span>
                    <span class="hl-lesson-ch" v-if="l.chapter">— {{ l.chapter }}</span>
                  </div>
                </div>
              </div>

              <div class="hl-hint">点击左侧章节查看逐章详情</div>
            </div>
            <template v-else>
              <div class="detail-section">
                <div class="detail-section-head">
                  <b>{{ selected.title }}</b>
                  <div style="display:flex;gap:8px">
                    <el-tag size="small" round>密度 {{ selected.density_score }}</el-tag>
                    <el-tag size="small" :type="statusTag(selected.analysis_status)" round>
                      {{ statusLabel(selected.analysis_status) }}
                    </el-tag>
                  </div>
                </div>

                <div v-if="behavior">
                  <p><b>场景</b>: {{ behavior.scene_summary }}</p>
                  <p v-if="behavior.characters_involved?.length">
                    <b>人物</b>:
                    <el-tag v-for="n in behavior.characters_involved" :key="n" size="small" round style="margin-right:5px">{{ n }}</el-tag>
                  </p>
                  <el-divider />
                  <div v-for="dim in dims" :key="dim.key">
                    <div v-if="behavior[dim.key]" class="dim-line">
                      <b>{{ dim.label }}</b>: {{ dimText(behavior[dim.key]) }}
                      <span v-if="behavior[dim.key].evidence" class="evidence">「{{ behavior[dim.key].evidence }}」</span>
                    </div>
                  </div>
                  <el-alert v-if="behavior.core_lesson" :title="behavior.core_lesson" type="success" :closable="false" class="lesson-alert" />
                  <div class="tag-row">
                    <el-tag v-for="t in behavior.tags" :key="t" type="info" size="small" round>{{ t }}</el-tag>
                  </div>
                </div>
                <el-empty v-else :description="selected.should_analyze ? '本章尚未分析' : '低密度章节，已跳过'" :image-size="60" />
              </div>

              <div class="detail-section" v-if="dialogues.length">
                <div class="detail-section-head"><b>对话精读</b>（{{ dialogues.length }} 段）</div>
                <div v-for="d in dialogues" :key="d.id" class="dialogue-block">
                  <div style="margin-bottom:4px">
                    <el-tag v-if="d.speaker_role" size="small" type="success" effect="dark" round>{{ d.speaker_role }}</el-tag>
                    <span style="margin-left:6px;font-size:13px;color:var(--muted-fg)">{{ speakerLabel(d.speaker) }} → {{ d.listener || '?' }}</span>
                  </div>
                  <div class="quote-banner">「{{ d.original_text }}」</div>
                  <el-collapse>
                    <el-collapse-item title="逐句拆解">
                      <div v-for="(s, i) in d.sentence_breakdown" :key="i" class="sent-block">
                        <div class="sent-text">「{{ s.sentence }}」</div>
                        <div class="sent-meta">意图: {{ s.real_intent }}</div>
                        <div class="tag-row" style="margin-top:4px">
                          <el-tag v-for="t in s.techniques" :key="t" size="small" type="warning" effect="light" round>{{ t }}</el-tag>
                        </div>
                      </div>
                    </el-collapse-item>
                  </el-collapse>
                  <div class="tag-row">
                    <el-tag v-for="t in d.techniques" :key="t" type="warning" effect="plain" size="small" round>{{ t }}</el-tag>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api, connectProgress } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const router = useRouter()
const bookId = Number(props.id)

const loading = ref(true)
const book = ref(null)
const chapters = ref([])
const selected = ref(null)
const behavior = ref(null)
const dialogues = ref([])
const progress = ref({ total: 0, analyzed: 0, failed: 0, pending: 0, current_chapter: '' })
const running = ref(false)
const aggregating = ref(false)
const heatmapOpen = ref(false)
const highlightLoading = ref(false)
const highlight = ref({
  behaviors: 0, dialogues: 0, rules: 0,
  techniques: [], rule_categories: [],
  techMax: 1, ruleMax: 1,
  lessons: [],
})
let ws = null
let pollTimer = null
let startTime = null
// 章节详情局部缓存 + 请求取消(避免重复请求与竞态覆盖)
const detailCache = new Map()
let abortController = null

const dims = [
  { key: 'loyalty_signaling', label: '表态信号' },
  { key: 'timing_of_alignment', label: '站队时机' },
  { key: 'leaving_traces', label: '留痕做事' },
  { key: 'relational_read', label: '关系定位' },
  { key: 'calibration', label: '进退分寸' },
  { key: 'long_term_tally', label: '长期账' },
]

const PRONOUNS = new Set(['他', '她', '它', '他们', '她们', '男主', '女主'])
function speakerLabel(s) { return (!s || PRONOUNS.has(s)) ? '主角' : s }

const progPct = computed(() => {
  const t = progress.value.total || 1
  return Math.round(((progress.value.analyzed + progress.value.failed) / t) * 100)
})
const progStatus = computed(() => {
  if (book.value?.status === 'completed') return 'success'
  if (progress.value.failed && !running.value) return 'warning'
  return ''
})
const eta = computed(() => {
  const s = progress.value.estimated_remaining_seconds
  if (!s) return ''
  if (s < 60) return `${s} 秒`
  if (s < 3600) return `${Math.round(s / 60)} 分钟`
  return `${(s / 3600).toFixed(1)} 小时`
})
const speed = computed(() => {
  if (!startTime) return '--'
  const done = progress.value.analyzed + (progress.value.failed || 0)
  if (done < 2) return '--'
  const elapsed = (Date.now() - startTime) / 1000 / 60
  if (elapsed < 0.1) return '--'
  return Math.round(done / elapsed)
})

function dimText(v) { return v.description || v.method || v.type || '' }
function densityShort(c) { return c.should_analyze ? Math.round(c.density_score) : '跳过' }
function statusTag(s) {
  return { pending: 'info', analyzing: 'warning', completed: 'success', failed: 'danger', skipped: 'info' }[s] || 'info'
}
function statusLabel(s) {
  return { pending: '待分析', analyzing: '分析中', completed: '已完成', failed: '失败', skipped: '已跳过' }[s] || s
}
function chCellClass(c) {
  const s = c.analysis_status
  if (s === 'completed') return 'c-success'
  if (s === 'analyzing') return 'c-running'
  if (s === 'failed') return 'c-failed'
  if (s === 'skipped') return 'c-skip'
  return 'c-pending'
}

async function loadBook() {
  const { data } = await api.getBook(bookId)
  book.value = data
  running.value = data.status === 'analyzing'
}
async function loadChapters() {
  const { data } = await api.listChapters(bookId)
  chapters.value = data
}
async function loadProgress() {
  const { data } = await api.getProgress(bookId)
  progress.value = data
  running.value = data.running
}

async function selectChapter(c) {
  selected.value = c
  behavior.value = null
  dialogues.value = []

  // 取消上一个未完成的请求,防止旧响应晚到覆盖当前选中章节
  if (abortController) { abortController.abort(); abortController = null }

  // 命中本地缓存,直接渲染,避免重复请求
  if (detailCache.has(c.id)) {
    const cached = detailCache.get(c.id)
    behavior.value = cached.behavior
    dialogues.value = cached.dialogues
    return
  }

  if (c.analysis_status === 'completed' || c.analysis_status === 'failed') {
    abortController = new AbortController()
    const signal = abortController.signal
    try {
      const [b, d] = await Promise.all([
        api.getBehavior(c.id, { signal }),
        api.getDialogues(c.id, { signal }),
      ])
      behavior.value = b.data
      dialogues.value = d.data
      detailCache.set(c.id, { behavior: b.data, dialogues: d.data })
    } catch (err) {
      // 主动取消的请求忽略,其它错误打印
      if (err?.code !== 'ERR_CANCELED' && err?.name !== 'CanceledError') {
        console.error('获取章节详情失败', err)
      }
    }
  }
}

async function analyze() { await api.startAnalyze(bookId); running.value = true; startTime = Date.now(); ElMessage.success('已启动'); ensureWs() }
async function stop() { await api.stopAnalyze(bookId); ElMessage.info('已请求中止') }
function exportMd() { window.open(api.exportMarkdownUrl(bookId), '_blank') }
function goto(sub) { router.push(`/books/${bookId}/${sub}`) }

function ensureWs() {
  if (ws) return
  ws = connectProgress(bookId, (msg) => {
    if (msg.type === 'progress') { progress.value = { ...progress.value, ...msg }; running.value = true; aggregating.value = false }
    else if (msg.type === 'aggregating') { aggregating.value = true }
    else if (msg.type === 'completed') {
      progress.value = { ...progress.value, analyzed: msg.analyzed, failed: msg.failed, total: msg.total }
      running.value = false; aggregating.value = false; ElMessage.success('分析完成'); refresh()
    } else if (msg.type === 'stopped') { running.value = false; refresh() }
    else if (msg.type === 'error') { running.value = false; ElMessage.error(msg.message || '分析出错'); refresh() }
  })
}

async function refresh() { await Promise.all([loadBook(), loadChapters(), loadProgress()]) }

async function loadHighlight() {
  highlightLoading.value = true
  try {
    const [statsRes, cardsRes] = await Promise.all([
      api.stats(bookId).catch(() => null),
      api.behaviorCards(bookId).catch(() => null),
    ])
    const s = statsRes?.data
    const cards = cardsRes?.data?.cards || []
    const techniques = (s?.techniques || []).slice(0, 5)
    const rule_categories = (s?.rule_categories || []).slice(0, 5)
    const lessons = cards
      .filter(c => c.core_lesson && c.core_lesson.length > 8)
      .slice(0, 6)
      .map(c => ({ text: c.core_lesson, chapter: c.chapter_title }))
    highlight.value = {
      behaviors: s?.counts?.behaviors || 0,
      dialogues: s?.counts?.dialogues || 0,
      rules: s?.counts?.rules || 0,
      techniques,
      rule_categories,
      techMax: Math.max(1, ...techniques.map(t => t[1])),
      ruleMax: Math.max(1, ...rule_categories.map(r => r[1])),
      lessons,
    }
  } finally {
    highlightLoading.value = false
  }
}

onMounted(async () => {
  try { await refresh() }
  catch { ElMessage({ message: '加载书籍详情失败,请稍后重试', type: 'error', grouping: true }) }
  finally { loading.value = false }
  // 进入书详情默认展示「本书亮点」面板，不自动选中章节
  loadHighlight()
  ensureWs()
  pollTimer = setInterval(() => { if (running.value) loadProgress() }, 5000)
})
onUnmounted(() => { if (ws) ws.close(); if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
/* ===== 工作台:整页占满视口高度,不外滚 ===== */
.detail-shell {
  height: calc(100vh - 3.5rem);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.detail-inner { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.detail-top { flex-shrink: 0; }

.head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; margin-bottom: 10px; }
.actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }

/* 醒目导航瓷砖 */
.nav-tiles { display: flex; gap: 10px; flex-wrap: wrap; }
/* 扁平化:纯色矩形,无阴影无位移,悬停仅变色 */
.nav-tile {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
  min-width: 76px; padding: 10px 14px; cursor: pointer;
  border: 1px solid var(--accent); border-radius: 6px;
  background: var(--accent); color: #fff;
  font-family: var(--font-body); font-size: 14px; font-weight: 600;
  transition: background-color .12s ease, color .12s ease, border-color .12s ease;
}
.nav-tile .el-icon { font-size: 20px; }
.nav-tile:hover { background: var(--accent-secondary); border-color: var(--accent-secondary); }
.nav-tile-ghost { background: var(--card); color: var(--accent); }
.nav-tile-ghost:hover { background: var(--accent-subtle); }

/* 紧凑单行进度 */
.prog-compact { display: flex; align-items: center; gap: 16px; }
.prog-stats-inline { display: flex; gap: 14px; font-size: 13px; color: var(--muted-fg); white-space: nowrap; }
.prog-stats-inline b { color: var(--fg); }
.prog-ctrl { flex-shrink: 0; display: flex; gap: 8px; align-items: center; }
.stat-item { display: flex; align-items: center; gap: 5px; }
.stat-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.stat-dot.done { background: var(--success); }
.stat-dot.pending-icon { background: var(--muted-fg); opacity: .4; }
.stat-dot.failed { background: var(--danger); }
.stat-dot.running-icon { background: var(--accent); }
.current-chap { margin-top: 6px; font-size: 13px; color: var(--accent); display: flex; align-items: center; gap: 6px; }

/* 章节地图(折叠) */
.ch-grid-wrap { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }
.ch-grid-title { display: flex; justify-content: flex-end; align-items: center; font-size: 12px; color: var(--muted-fg); margin-bottom: 8px; }
.ch-legend { display: flex; gap: 12px; }
.ch-legend-item { display: flex; align-items: center; gap: 4px; }
.ch-legend-dot { width: 8px; height: 8px; border-radius: 2px; display: inline-block; }
.ch-legend-dot.c-success { background: var(--success); }
.ch-legend-dot.c-running { background: var(--accent); }
.ch-legend-dot.c-pending { background: var(--border); }
.ch-legend-dot.c-failed { background: var(--danger); }
.ch-legend-dot.c-skip { background: var(--muted); }
.ch-grid { display: flex; flex-wrap: wrap; gap: 2px; max-height: 22vh; overflow-y: auto; }
.ch-cell { width: 12px; height: 12px; border-radius: 2px; cursor: pointer; transition: transform .15s; }
.ch-cell:hover { transform: scale(1.6); z-index: 1; position: relative; }
.ch-cell.c-success { background: var(--success); }
.ch-cell.c-running { background: var(--accent); }
.ch-cell.c-pending { background: var(--border); }
.ch-cell.c-failed { background: var(--danger); }
.ch-cell.c-skip { background: var(--muted); opacity: .5; }

/* ===== 主体两栏 ===== */
.detail-main { flex: 1; min-height: 0; display: flex; gap: 16px; margin-top: 14px; }
.pane {
  border: 1px solid var(--border); border-radius: 8px; background: var(--card);
  display: flex; flex-direction: column; min-height: 0; overflow: hidden;
}
.pane-list { width: 320px; flex-shrink: 0; }
.pane-detail { flex: 1; min-width: 0; }
.pane-head { flex-shrink: 0; padding: 12px 16px; border-bottom: 1px solid var(--border); }
.pane-body { flex: 1; overflow-y: auto; min-height: 0; }
.detail-body { padding: 18px 20px; }

.chapter-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; border-bottom: 1px solid var(--border); gap: 10px; transition: background .15s;
}
.chapter-item:hover { background: var(--muted); }
.chapter-item.active { background: var(--accent-subtle); box-shadow: inset 3px 0 0 var(--accent); }
.chapter-item.skip .ch-title { color: var(--muted-fg); opacity: .5; }
.ch-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }

/* 手机:两栏改上下堆叠,导航瓷砖缩小 */
@media (max-width: 768px) {
  .detail-shell { height: auto; overflow: visible; }
  .detail-main { flex-direction: column; }
  .pane-list { width: auto; max-height: 38vh; }
  .nav-tiles { gap: 6px; }
  .nav-tile { min-width: 60px; padding: 8px 8px; font-size: 12px; }
  .nav-tile .el-icon { font-size: 17px; }
  .prog-compact { flex-wrap: wrap; }
}

/* ===== 亮点面板（书详情默认主面板）===== */
.highlight-panel { padding: 4px 2px 16px; }
.hl-header { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; padding-bottom: 12px; border-bottom: 2px solid var(--accent); }
.hl-title { font-family: var(--font-display); font-size: 1.35rem; font-weight: 600; color: var(--fg); }
.hl-sub { font-size: 13px; color: var(--muted-fg); margin-top: 4px; }
.hl-more { color: var(--accent); }

.hl-kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 22px; }
.hl-kpi { border: 1px solid var(--border); border-radius: 8px; background: var(--card); padding: 14px 16px; }
.hl-kpi .kn { font-family: var(--font-display); font-size: 1.6rem; font-weight: 600; color: var(--accent); line-height: 1; }
.hl-kpi .kl { font-size: 12.5px; color: var(--muted-fg); margin-top: 6px; }

.hl-twocol { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 22px; }
.hl-col { border: 1px solid var(--border); border-radius: 8px; background: var(--card); padding: 14px 16px; }
.hl-col-title { font-family: var(--font-display); font-size: 14px; font-weight: 600; color: var(--fg); margin-bottom: 10px; }
.hl-bar-list { display: flex; flex-direction: column; gap: 7px; }
.hl-bar-row {
  display: grid; grid-template-columns: 20px 130px 1fr 40px; align-items: center; gap: 8px;
  cursor: pointer; padding: 4px 4px; border-radius: 4px;
  transition: background-color .12s;
}
.hl-bar-row:hover { background: var(--accent-subtle); }
.hl-rank { font-family: var(--font-mono); font-size: 11px; color: var(--accent); font-weight: 700; text-align: right; }
.hl-bar-label { font-size: 13px; color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hl-bar-track { background: var(--muted); border-radius: 99px; height: 9px; overflow: hidden; }
.hl-bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent-secondary, var(--accent))); border-radius: 99px; transition: width .45s; }
.hl-bar-val { font-family: var(--font-mono); font-size: 12px; color: var(--fg); font-weight: 600; text-align: right; }

.hl-lessons { margin-bottom: 16px; }
.hl-lesson-list { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.hl-lesson-item {
  border-left: 3px solid var(--accent); background: var(--muted);
  padding: 10px 14px; border-radius: 0 6px 6px 0; cursor: pointer;
  font-size: 13.5px; line-height: 1.6; color: var(--fg);
  transition: background-color .12s, border-color .12s;
  position: relative;
}
.hl-lesson-item:hover { background: var(--accent-subtle); border-color: var(--accent-secondary, var(--accent)); }
.hl-quote-mark { font-family: var(--font-display); font-size: 1.4rem; color: var(--accent); margin-right: 4px; line-height: 0; vertical-align: -0.3em; }
.hl-lesson-text { color: var(--fg); }
.hl-lesson-ch { font-size: 12px; color: var(--muted-fg); margin-left: 8px; white-space: nowrap; }
.hl-hint { font-size: 12px; color: var(--muted-fg); text-align: center; margin-top: 18px; padding-top: 12px; border-top: 1px dashed var(--border); }

@media (max-width: 900px) {
  .hl-kpis { grid-template-columns: 1fr 1fr; }
  .hl-twocol { grid-template-columns: 1fr; }
  .hl-bar-row { grid-template-columns: 20px 100px 1fr 36px; }
}

.detail-section { margin-bottom: 18px; }
.detail-section-head { display: flex; justify-content: space-between; align-items: center; padding-bottom: 10px; margin-bottom: 12px; border-bottom: 1px solid var(--border); }
.dim-line { margin: 6px 0; line-height: 1.6; }
.lesson-alert { margin: 12px 0; }
.quote-banner { background: var(--muted); padding: 8px 12px; border-left: 3px solid var(--accent); border-radius: 4px; margin: 6px 0; }
.dialogue-block { padding: 14px 0; border-bottom: 1px dashed var(--border); }
.dialogue-block:last-child { border-bottom: none; }
.sent-block { margin-bottom: 10px; }
.sent-meta { font-size: 13px; color: var(--muted-fg); }
</style>
