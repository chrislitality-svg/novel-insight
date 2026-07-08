<template>
  <div class="page" v-loading="loading">
    <div class="bar-header">
      <div>
        <h2 class="page-title">对话策略</h2>
        <p class="page-subtitle">默认只看原文与技巧，点「展开拆解」再看潜台词 / 话术结构 / 逐句</p>
      </div>
      <el-button @click="$router.push(`/books/${id}`)" plain round size="small">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
    </div>

    <!-- 顶部横向 chip 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-row" v-if="facets.speaker_roles && facets.speaker_roles.length">
        <span class="filter-label">角色</span>
        <div class="chip-wrap" :class="{ collapsed: !roleExpanded }">
          <button class="chip" :class="{ active: !speakerRole }" @click="speakerRole = ''; reload()">全部</button>
          <button v-for="[r, n] in facets.speaker_roles" :key="r" class="chip"
            :class="{ active: speakerRole === r }" @click="speakerRole = r; reload()">
            {{ r }} <span class="chip-n">{{ n }}</span>
          </button>
        </div>
        <button v-if="facets.speaker_roles.length > 10" class="more-btn" @click="roleExpanded = !roleExpanded">
          {{ roleExpanded ? '收起 ▴' : '更多 ▾' }}
        </button>
      </div>
      <div class="filter-row" v-if="facets.scenarios && facets.scenarios.length">
        <span class="filter-label">场景</span>
        <div class="chip-wrap" :class="{ collapsed: !scenarioExpanded }">
          <button class="chip" :class="{ active: !scenario }" @click="scenario = ''; reload()">全部</button>
          <button v-for="[s, n] in facets.scenarios" :key="s" class="chip"
            :class="{ active: scenario === s }" @click="scenario = s; reload()">
            {{ s }} <span class="chip-n">{{ n }}</span>
          </button>
        </div>
        <button v-if="facets.scenarios.length > 10" class="more-btn" @click="scenarioExpanded = !scenarioExpanded">
          {{ scenarioExpanded ? '收起 ▴' : '更多 ▾' }}
        </button>
      </div>
      <div class="filter-row" v-if="facets.techniques && facets.techniques.length">
        <span class="filter-label">技巧</span>
        <div class="chip-wrap" :class="{ collapsed: !techExpanded }">
          <button class="chip" :class="{ active: !technique }" @click="technique = ''; reload()">全部</button>
          <button v-for="[t, n] in facets.techniques" :key="t" class="chip"
            :class="{ active: technique === t }" @click="technique = t; reload()">
            {{ t }} <span class="chip-n">{{ n }}</span>
          </button>
        </div>
        <button v-if="facets.techniques.length > 10" class="more-btn" @click="techExpanded = !techExpanded">
          {{ techExpanded ? '收起 ▴' : '更多 ▾' }}
        </button>
      </div>
    </div>

    <div class="list-head">
      <span class="muted">
        共 <b>{{ cards.length }}</b> 条策略
        <span v-if="technique" style="color:var(--accent)"> · {{ technique }}</span>
        <span v-if="scenario" style="color:var(--accent)"> · {{ scenario }}</span>
      </span>
      <div style="display:flex; gap:10px; align-items:center">
        <el-button text size="small" @click="toggleAll">{{ allOpen ? '全部收起' : '全部展开' }}</el-button>
        <el-pagination v-if="cards.length > pageSize" size="small" background
          layout="prev, pager, next" :total="cards.length" :page-size="pageSize"
          v-model:current-page="page" @current-change="toTop" />
      </div>
    </div>
    <el-empty v-if="!loading && cards.length === 0" description="暂无对话策略" />

        <div class="dlg-grid">
          <div v-for="d in paged" :key="d.id" class="grid-item">
            <el-card shadow="never" :body-style="{ padding: 0 }">

              <!-- 紧凑区:场景 + 说话人 + 原文 + 技巧 + 一句话 -->
              <div class="quote-section">
                <div class="quote-speaker">
                  <el-tag v-if="d.scenario" effect="dark" type="primary" round size="small">{{ d.scenario }}</el-tag>
                  <el-tag v-if="d.speaker_role" size="small" effect="plain" type="success" round>{{ d.speaker_role }}</el-tag>
                  <span class="speaker-name">{{ speakerLabel(d.speaker) }}</span>
                  <span class="speaker-arrow">→</span>
                  <span class="speaker-name">{{ d.listener || '?' }}</span>
                </div>
                <div class="quote-body">「{{ d.original_text }}」</div>
              </div>

              <div class="compact-foot">
                <div class="tag-row">
                  <el-tag v-for="t in d.techniques" :key="t" type="warning" effect="plain" size="small" round
                    class="tag-click" @click="technique = t; reload()">{{ t }}</el-tag>
                </div>
                <div v-if="d.lesson" class="lesson-line"><el-icon class="lesson-icon"><Opportunity /></el-icon>{{ d.lesson }}</div>
                <button class="expand-btn" @click="toggle(d.id)">
                  {{ openMap[d.id] ? '收起 ▲' : '展开拆解 · 潜台词 / 话术结构 / 逐句 ▼' }}
                </button>
              </div>

              <!-- 详情区:点击展开(动画) -->
              <el-collapse-transition>
                <div v-show="openMap[d.id]" class="detail-zone">
                  <div v-if="d.speech_template" class="template-banner">
                    <span class="tmpl-label">话术公式</span>{{ d.speech_template }}
                  </div>
                  <div v-if="d.subtext" class="subtext-box"><b>潜台词</b>&nbsp; {{ d.subtext }}</div>

                  <div v-if="d.speech_structure?.length" style="margin-top:.75rem">
                    <div class="analysis-header">
                      <span class="analysis-label">分步拆解</span>
                      <span class="muted">先说什么 → 再说什么 → 为什么</span>
                    </div>
                    <div class="structure-list">
                      <div v-for="(st, i) in d.speech_structure" :key="i" class="structure-step">
                        <div class="step-num">{{ i + 1 }}</div>
                        <div class="step-content">
                          <div class="step-what">{{ st.content }}</div>
                          <div class="step-why">{{ st.purpose }}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-if="d.sentence_breakdown?.length" style="margin-top:.75rem">
                    <div class="analysis-header"><span class="analysis-label">逐句精读</span></div>
                    <div v-for="(s, i) in d.sentence_breakdown" :key="i" class="sent-block">
                      <div class="sent-quote">「{{ s.sentence }}」</div>
                      <div class="sent-meta">意图：{{ s.real_intent }}</div>
                      <div class="tag-row" style="margin-top:4px">
                        <el-tag v-for="t in s.techniques" :key="t" size="small" type="warning" effect="light" round>{{ t }}</el-tag>
                      </div>
                    </div>
                  </div>
                </div>
              </el-collapse-transition>

        </el-card>
      </div>
    </div>

    <div class="list-foot" v-if="cards.length > pageSize">
      <el-pagination background layout="prev, pager, next, jumper, total"
        :total="cards.length" :page-size="pageSize"
        v-model:current-page="page" @current-change="toTop" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ArrowLeft, Opportunity } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const id = Number(props.id)

const loading = ref(true)
const cards = ref([])
const facets = ref({ techniques: [], speaker_roles: [], scenarios: [] })
const technique = ref('')
const speakerRole = ref('')
const scenario = ref('')
const page = ref(1)
const pageSize = 24
const openMap = reactive({})
const allOpen = ref(false)
const roleExpanded = ref(false)
const scenarioExpanded = ref(false)
const techExpanded = ref(false)

const paged = computed(() => cards.value.slice((page.value - 1) * pageSize, page.value * pageSize))
function toTop() { window.scrollTo({ top: 0, behavior: 'smooth' }) }
function toggle(idv) { openMap[idv] = !openMap[idv] }
function toggleAll() {
  allOpen.value = !allOpen.value
  paged.value.forEach((d) => { openMap[d.id] = allOpen.value })
}

const PRONOUNS = new Set(['他', '她', '它', '他们', '她们', '男主', '女主'])
function speakerLabel(s) { return (!s || PRONOUNS.has(s)) ? '主角' : s }

async function reload() {
  loading.value = true
  page.value = 1
  try {
    const params = {}
    if (technique.value) params.technique = technique.value
    if (speakerRole.value) params.speaker_role = speakerRole.value
    if (scenario.value) params.scenario = scenario.value
    const { data } = await api.dialogueCards(id, params)
    cards.value = data.cards
    facets.value = data.facets
  } catch {
    ElMessage({ message: '加载对话策略失败,请稍后重试', type: 'error', grouping: true })
  } finally { loading.value = false }
}
onMounted(reload)
</script>

<style scoped>
/* 顶部 chip 筛选栏 */
.filter-bar {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--card);
  padding: 12px 16px;
  margin-bottom: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.filter-row { display: flex; align-items: flex-start; gap: 10px; flex-wrap: nowrap; }
.filter-label {
  flex-shrink: 0; font-size: 13px; color: var(--muted-fg);
  padding-top: 4px; min-width: 32px;
}
.chip-wrap {
  display: flex; flex-wrap: wrap; gap: 6px;
  flex: 1; min-width: 0;
  max-height: 32px; overflow: hidden;
  transition: max-height .2s ease;
}
.chip-wrap:not(.collapsed) { max-height: 240px; overflow-y: auto; }
.chip {
  border: 1px solid var(--border); background: var(--muted); color: var(--fg);
  font-size: 12.5px; padding: 4px 11px; border-radius: 999px; cursor: pointer;
  white-space: nowrap; line-height: 1.4;
  transition: background-color .12s, border-color .12s, color .12s;
}
.chip:hover { background: var(--accent-subtle); border-color: var(--accent); color: var(--accent); }
.chip.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.chip.active .chip-n { color: rgba(255,255,255,.75); }
.chip-n { font-size: 11px; color: var(--muted-fg); margin-left: 2px; }
.more-btn {
  flex-shrink: 0; border: 1px solid var(--border); background: transparent; color: var(--accent);
  font-size: 12px; padding: 4px 10px; border-radius: 999px; cursor: pointer;
  align-self: flex-start;
}
.more-btn:hover { background: var(--accent-subtle); }

.list-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }
.list-foot { display: flex; justify-content: center; margin-top: 1.5rem; }
.dlg-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(340px, 100%), 1fr)); gap: 1.25rem; align-items: start; }

.quote-section { padding: 14px 16px 10px; }
.quote-speaker { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; font-size: 13px; }
.speaker-name { font-weight: 600; color: var(--fg); }
.speaker-arrow { color: var(--muted-fg); }
.quote-body { background: var(--muted); border-left: 3px solid var(--accent); border-radius: 0 6px 6px 0; padding: 8px 12px; line-height: 1.7; font-size: 14px; color: var(--fg); }

.compact-foot { padding: 0 16px 14px; }
.lesson-line { margin-top: 8px; font-size: 13px; color: #5a4a1a; background: #fdfaf3; border: 1px solid #f0e4c6; border-radius: 6px; padding: 6px 10px; line-height: 1.6; }
.expand-btn {
  margin-top: 10px; width: 100%; border: 1px dashed var(--border); background: transparent;
  color: var(--accent); font-size: 12.5px; padding: 7px; border-radius: 6px; cursor: pointer;
  transition: background-color .12s ease, border-color .12s ease;
}
.expand-btn:hover { background: #fdf6e3; border-color: var(--accent); }

.detail-zone { padding: 0 16px 16px; border-top: 1px solid var(--border); margin-top: 2px; padding-top: 12px; }
.analysis-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.analysis-label { font-family: var(--font-mono); font-size: .6875rem; letter-spacing: .12em; color: var(--accent); text-transform: uppercase; }
</style>
