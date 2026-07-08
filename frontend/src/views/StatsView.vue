<template>
  <div class="page" v-loading="loading">
    <div class="bar-header">
      <div>
        <h2 class="page-title">量化分析</h2>
        <p class="page-subtitle">{{ s?.title ? `《${s.title}》 — ` : '' }}最常用的话术技巧、沟通方式、表态强度等频次统计</p>
      </div>
      <el-button @click="$router.push(`/books/${id}`)" plain round size="small">
        <el-icon><ArrowLeft /></el-icon> 返回书籍
      </el-button>
    </div>

    <template v-if="s">
      <!-- 书籍概览 -->
      <div class="overview-card">
        <div class="overview-meta">
          <span v-if="bookInfo?.author" class="meta-item"><span class="meta-label">作者</span>{{ bookInfo.author }}</span>
          <span v-if="s.protagonist" class="meta-item"><span class="meta-label">主角</span>{{ s.protagonist }}</span>
          <span v-if="s.setting" class="meta-item"><span class="meta-label">背景</span>{{ s.setting }}</span>
        </div>
        <div class="overview-progress" v-if="bookInfo">
          <span class="progress-text">已分析 <b>{{ bookInfo.analyzed_chapters }}</b> / <b>{{ bookInfo.total_chapters }}</b> 章</span>
          <div class="progress-bar-mini">
            <div class="progress-fill-mini" :style="{ width: progressPct + '%' }"></div>
          </div>
          <span class="progress-pct">{{ progressPct }}%</span>
        </div>
      </div>

      <!-- 核心指标 -->
      <div class="kpis">
        <div class="kpi">
          <div class="kpi-icon kpi-icon--dialogue">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          </div>
          <div class="kpi-body">
            <div class="kpi-n">{{ s.counts.dialogues }}</div>
            <div class="kpi-l">对话样本</div>
          </div>
        </div>
        <div class="kpi">
          <div class="kpi-icon kpi-icon--behavior">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <div class="kpi-body">
            <div class="kpi-n">{{ s.counts.behaviors }}</div>
            <div class="kpi-l">做派样本</div>
          </div>
        </div>
        <div class="kpi">
          <div class="kpi-icon kpi-icon--rules">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          </div>
          <div class="kpi-body">
            <div class="kpi-n">{{ s.counts.rules }}</div>
            <div class="kpi-l">提炼规则</div>
          </div>
        </div>
        <div class="kpi">
          <div class="kpi-icon kpi-icon--signal">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          </div>
          <div class="kpi-body">
            <div class="kpi-n">{{ s.avg_signal || '—' }}</div>
            <div class="kpi-l">平均表态强度 <span class="kpi-unit">/ 5</span></div>
          </div>
        </div>
      </div>

      <!-- 分析摘要 -->
      <div class="summary-box">
        <div class="summary-title">分析摘要</div>
        <p class="summary-text">{{ summaryText }}</p>
      </div>

      <div class="charts">
        <enhanced-bar-chart
          title="话术技巧 TOP 15"
          subtitle="最常用的沟通话术与修辞技巧"
          :data="s.techniques"
          color="#8C7355"
          show-rank
        />
        <enhanced-bar-chart
          title="高频对话场景"
          subtitle="对话发生的典型社交情境"
          :data="s.scenarios"
          color="#6B7B8C"
          show-rank
        />
        <div class="chart-card signal-card">
          <div class="chart-title-row">
            <span class="chart-title">表态强度分布</span>
            <span class="chart-subtitle">1=含蓄委婉 · 5=直接强硬</span>
          </div>
          <div class="signal-gauges">
            <div v-for="(item, i) in strengthData" :key="i" class="signal-item" :class="'signal-lvl-' + (i + 1)">
              <span class="signal-label">{{ item[0] }}</span>
              <div class="signal-track">
                <div class="signal-fill" :style="{ width: signalPct(i) + '%' }"></div>
              </div>
              <span class="signal-val">{{ item[1] }}次</span>
            </div>
          </div>
          <div class="signal-avg" v-if="s.avg_signal">
            整体偏向：
            <span class="signal-tag" :class="signalLevel">{{ signalLevelText }}</span>
          </div>
        </div>
        <enhanced-bar-chart
          title="说话人角色分布"
          subtitle="对话中各方角色的出场频次"
          :data="s.speaker_roles"
          color="#7A6E6B"
          show-rank
          v-if="s.speaker_roles.length"
        />
        <enhanced-bar-chart
          title="做派标签 TOP 15"
          subtitle="行为做派的高频标签"
          :data="s.tags"
          color="#6B7A6B"
          show-rank
        />
        <enhanced-bar-chart
          title="社会规则分类"
          subtitle="人情世故规则的领域分布"
          :data="s.rule_categories"
          color="#8A7A6B"
          show-rank
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, h, onMounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const id = Number(props.id)
const loading = ref(true)
const s = ref(null)
const bookInfo = ref(null)

const progressPct = computed(() => {
  if (!bookInfo.value) return 0
  const { total_chapters, analyzed_chapters } = bookInfo.value
  if (!total_chapters) return 0
  return Math.round((analyzed_chapters / total_chapters) * 100)
})

const strengthData = computed(() => (s.value?.signal_strength || []).map(([k, v]) => [`${k} 分`, v]))

const strengthMax = computed(() => Math.max(1, ...(s.value?.signal_strength || []).map(([, v]) => v)))

const signalPct = (i) => {
  if (!s.value?.signal_strength) return 0
  return Math.round((s.value.signal_strength[i][1] / strengthMax.value) * 100)
}

const signalLevel = computed(() => {
  const avg = s.value?.avg_signal || 0
  if (avg < 2.5) return 'level-low'
  if (avg < 3.5) return 'level-mid'
  return 'level-high'
})

const signalLevelText = computed(() => {
  const avg = s.value?.avg_signal || 0
  if (avg < 2.5) return '含蓄委婉型'
  if (avg < 3.5) return '刚柔并济型'
  return '直接强硬型'
})

const summaryText = computed(() => {
  if (!s.value) return ''
  const parts = []
  if (s.value.techniques?.length) {
    const top3 = s.value.techniques.slice(0, 3).map(([t]) => t).join('、')
    parts.push(`全书对话最倚重「${top3}」等话术技巧`)
  }
  if (s.value.scenarios?.length) {
    parts.push(`高频场景集中在「${s.value.scenarios[0][0]}」`)
  }
  if (s.value.tags?.length) {
    parts.push(`整体做派偏向「${s.value.tags[0][0]}」`)
  }
  if (s.value.avg_signal) {
    parts.push(`表态强度均值为 ${s.value.avg_signal}/5，偏${signalLevelText.value}`)
  }
  if (s.value.rule_categories?.length) {
    parts.push(`社会规则以「${s.value.rule_categories[0][0]}」领域最多`)
  }
  return parts.join('；') + '。'
})

// 增强版条形图:支持排名、颜色、副标题
const EnhancedBarChart = (props) => {
  const data = props.data || []
  const max = Math.max(1, ...data.map((d) => d[1]))
  const total = data.reduce((s, d) => s + d[1], 0)
  return h('div', { class: 'chart-card' }, [
    h('div', { class: 'chart-title-row' }, [
      h('span', { class: 'chart-title' }, props.title),
      props.subtitle ? h('span', { class: 'chart-subtitle' }, props.subtitle) : null,
    ]),
    data.length === 0
      ? h('div', { class: 'muted', style: 'padding:8px 0' }, '暂无数据')
      : h('div', { class: 'bars' }, data.map(([label, val], idx) => {
          const pct = total > 0 ? Math.round((val / total) * 100) : 0
          const c = props.color || 'var(--accent)'
          const grad = c.startsWith('#')
            ? `linear-gradient(90deg, ${c}99 0%, ${c} 100%)`
            : `linear-gradient(90deg, ${c} 0%, ${c} 100%)`
          return h('div', { class: 'bar-row bar-row--enhanced' }, [
            props.showRank ? h('span', { class: 'bar-rank' + (idx < 3 ? ' top3' : '') }, idx + 1) : null,
            h('span', { class: 'bar-label', title: label }, label),
            h('div', { class: 'bar-track' }, [
              h('div', {
                class: 'bar-fill',
                style: `width:${Math.round((val / max) * 100)}%; background:${grad}`,
              }),
            ]),
            h('span', { class: 'bar-val' }, String(val)),
            h('span', { class: 'bar-pct' }, pct + '%'),
          ])
        })),
  ])
}
EnhancedBarChart.props = ['title', 'subtitle', 'data', 'color', 'showRank']

onMounted(async () => {
  try {
    const [statsRes, bookRes] = await Promise.all([
      api.stats(id),
      api.getBook(id).catch(() => null),
    ])
    s.value = statsRes.data
    if (bookRes) bookInfo.value = bookRes.data
  } catch {
    ElMessage({ message: '加载量化分析失败,请稍后重试', type: 'error', grouping: true })
  } finally {
    loading.value = false
  }
})
</script>

<!-- 非 scoped:EnhancedBarChart 由渲染函数生成,其内层元素不带 scoped 作用域 id,
     故样式需全局生效。本组件类名均为 StatsView 专用(已核对无冲突)。 -->
<style>
/* ===== 书籍概览 ===== */
.overview-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card);
  padding: 14px 18px;
  margin-bottom: 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.overview-meta { display: flex; flex-wrap: wrap; gap: 8px 18px; }
.meta-item { font-size: 13px; color: var(--fg); display: flex; align-items: center; gap: 6px; }
.meta-label {
  font-family: var(--font-mono);
  font-size: .625rem;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--muted-fg);
  background: var(--muted);
  padding: 2px 8px;
  border-radius: 3px;
}
.overview-progress { display: flex; align-items: center; gap: 10px; }
.progress-text { font-size: 12px; color: var(--muted-fg); white-space: nowrap; }
.progress-text b { color: var(--fg); font-weight: 600; }
.progress-bar-mini { width: 80px; height: 6px; background: var(--muted); border-radius: 99px; overflow: hidden; }
.progress-fill-mini { height: 100%; background: var(--accent); border-radius: 99px; transition: width .4s ease; }
.progress-pct { font-family: var(--font-mono); font-size: 12px; color: var(--accent); font-weight: 500; min-width: 32px; }

/* ===== KPIs ===== */
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 18px; }
.kpi {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.kpi-icon {
  width: 44px; height: 44px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.kpi-icon--dialogue  { background: #F5F2ED; color: #8C7355; }
.kpi-icon--behavior  { background: #F0F2F4; color: #6B7B8C; }
.kpi-icon--rules     { background: #F2F0F0; color: #7A6E6B; }
.kpi-icon--signal    { background: #F5F0EC; color: #9B6B4A; }
.kpi-body { min-width: 0; }
.kpi-n { font-family: var(--font-display); font-size: 1.8rem; font-weight: 600; color: var(--fg); line-height: 1.15; }
.kpi-l { font-size: 12px; color: var(--muted-fg); margin-top: 2px; }
.kpi-unit { color: var(--muted-fg); font-size: 11px; }

/* ===== 分析摘要 ===== */
.summary-box {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--accent-subtle);
  padding: 16px 20px;
  margin-bottom: 20px;
  border-left: 2px solid var(--accent);
}
.summary-title {
  font-family: var(--font-mono);
  font-size: .6875rem;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 8px;
}
.summary-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.75;
  color: var(--fg);
  font-family: var(--font-body);
}

/* ===== Charts Grid ===== */
.charts { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 16px; }

/* ===== Chart Card ===== */
.chart-card { border: 1px solid var(--border); border-radius: 8px; background: var(--card); padding: 18px 20px; }
.chart-title-row { display: flex; align-items: baseline; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.chart-title {
  font-family: var(--font-mono);
  font-size: .6875rem;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--accent);
}
.chart-subtitle {
  font-size: 12px;
  color: var(--muted-fg);
}

/* ===== Enhanced Bars ===== */
.bars { display: flex; flex-direction: column; gap: 7px; }
.bar-row--enhanced { display: grid; grid-template-columns: 24px 200px 1fr 48px 38px; align-items: center; gap: 8px; }
.bar-rank {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--muted-fg);
  text-align: right;
  font-weight: 600;
}
.bar-rank.top3 { color: var(--accent); font-weight: 700; }
.bar-label {
  font-size: 13px;
  color: var(--fg);
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.bar-track { background: var(--muted); border-radius: 99px; height: 12px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 99px; min-width: 4px; transition: width .45s cubic-bezier(0.16, 1, 0.3, 1); }
.bar-val {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--fg);
  text-align: right;
}
.bar-pct {
  font-size: 11px;
  color: var(--muted-fg);
  text-align: right;
  font-family: var(--font-mono);
}

/* ===== 表态强度分布 ===== */
.signal-card { border-left: 2px solid var(--accent); }
.signal-gauges { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; }
.signal-item { display: grid; grid-template-columns: 48px 1fr 48px; align-items: center; gap: 12px; }
.signal-label { font-size: 13px; color: var(--fg); text-align: right; font-family: var(--font-mono); }
.signal-track { background: var(--muted); border-radius: 99px; height: 12px; overflow: hidden; }
.signal-fill { height: 100%; border-radius: 99px; min-width: 4px; transition: width .45s cubic-bezier(0.16, 1, 0.3, 1); }
/* 表态强度色谱:1 含蓄(浅麦灰) → 3 主金 → 5 强硬(警示红) */
.signal-lvl-1 .signal-fill { background: linear-gradient(90deg, #d4cbc0, #c4b9aa); }
.signal-lvl-2 .signal-fill { background: linear-gradient(90deg, #c8b89e, #b89a72); }
.signal-lvl-3 .signal-fill { background: linear-gradient(90deg, #9b8a78, var(--accent)); }
.signal-lvl-4 .signal-fill { background: linear-gradient(90deg, var(--accent), #cd8a55); }
.signal-lvl-5 .signal-fill { background: linear-gradient(90deg, var(--accent), var(--danger)); }
.signal-val { font-size: 12px; color: var(--muted-fg); font-family: var(--font-mono); }
.signal-avg { font-size: 13px; color: var(--muted-fg); margin-top: 4px; }
.signal-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 500;
}
.signal-tag.level-low  { background: var(--accent-subtle); color: var(--accent); }
.signal-tag.level-mid  { background: #F0EBE4; color: #6B5A45; }
.signal-tag.level-high { background: #F0EBE4; color: #4A3A2A; }

/* ===== 深色模式:替换硬编码浅色块 ===== */
[data-theme="dark"] .kpi-icon--dialogue { background: #2a2620; color: #c8a06f; }
[data-theme="dark"] .kpi-icon--behavior { background: #20262b; color: #8fa6bb; }
[data-theme="dark"] .kpi-icon--rules    { background: #272324; color: #b59f97; }
[data-theme="dark"] .kpi-icon--signal   { background: #2a2218; color: #c89a6a; }
[data-theme="dark"] .signal-tag.level-mid  { background: #2a2620; color: #d8bd86; }
[data-theme="dark"] .signal-tag.level-high { background: #2a2218; color: #e0c79a; }

@media (max-width: 760px) {
  .charts { grid-template-columns: 1fr; }
  .bar-row--enhanced { grid-template-columns: 20px 110px 1fr 38px 32px; gap: 4px; }
  .overview-card { flex-direction: column; align-items: flex-start; }
  .kpis { grid-template-columns: repeat(2, 1fr); }
  .kpi { padding: 14px; gap: 10px; }
  .kpi-icon { width: 36px; height: 36px; }
}
@media (max-width: 480px) {
  .kpis { grid-template-columns: 1fr 1fr; }
  .bar-row--enhanced { grid-template-columns: 18px 90px 1fr 34px 28px; gap: 4px; }
}
</style>
