<template>
  <div class="page" v-loading="loading">
    <div class="bar-header">
      <div>
        <h2 class="page-title">两本书对比</h2>
        <p class="page-subtitle">同样是「上岸分手·重生逆袭」,两本书的人情世故侧重有何不同</p>
      </div>
      <el-button @click="$router.push('/books')" plain round size="small">
        <el-icon><ArrowLeft /></el-icon> 返回书架
      </el-button>
    </div>

    <!-- 选择两本书 -->
    <div class="pickers">
      <el-select v-model="idA" placeholder="书 A" size="default" @change="reload" style="width:320px">
        <el-option v-for="bk in books" :key="bk.id" :value="bk.id" :label="bk.title" />
      </el-select>
      <span class="vs">VS</span>
      <el-select v-model="idB" placeholder="书 B" size="default" @change="reload" style="width:320px">
        <el-option v-for="bk in books" :key="bk.id" :value="bk.id" :label="bk.title" />
      </el-select>
    </div>

    <template v-if="data">
      <!-- 我的对比结论(仅书1 vs 书2 时给出) -->
      <el-card v-if="verdict.length" shadow="never" class="verdict">
        <div class="section-label">对比结论</div>
        <ul>
          <li v-for="(v,i) in verdict" :key="i"><b>{{ v.k }}</b>:{{ v.t }}</li>
        </ul>
      </el-card>

      <!-- 各自优劣势 + 主角策略对比(书1 vs 书2)-->
      <template v-if="lore12">
        <div class="section-label" style="margin-top:6px">各自优劣势</div>
        <div class="sw-grid">
          <div class="sw-col" v-for="lore in [loreA, loreB]" :key="lore.name">
            <div class="sw-title">{{ lore.title }} · {{ lore.name }}</div>
            <div class="sw-sub pros">优势 / 看点</div>
            <ul><li v-for="(x,i) in lore.pros" :key="i">{{ x }}</li></ul>
            <div class="sw-sub cons">劣势 / 局限</div>
            <ul><li v-for="(x,i) in lore.cons" :key="i">{{ x }}</li></ul>
          </div>
        </div>

        <div class="section-label" style="margin-top:22px">主角策略对比</div>
        <div class="cmp-grid">
          <div class="cmp-col cmp-head"></div>
          <div class="cmp-col cmp-head book">{{ loreA.name }}</div>
          <div class="cmp-col cmp-head book">{{ loreB.name }}</div>
          <template v-for="row in strategyRows" :key="row.k">
            <div class="cmp-col cmp-label">{{ row.k }}</div>
            <div class="cmp-col">{{ row[String(data.a.id)] }}</div>
            <div class="cmp-col">{{ row[String(data.b.id)] }}</div>
          </template>
        </div>
      </template>

      <!-- 对照表 -->
      <div class="cmp-grid">
        <div class="cmp-col cmp-head"></div>
        <div class="cmp-col cmp-head book">《{{ data.a.title }}》</div>
        <div class="cmp-col cmp-head book">《{{ data.b.title }}》</div>

        <template v-for="row in rows" :key="row.key">
          <div class="cmp-col cmp-label">{{ row.label }}</div>
          <div class="cmp-col"><component :is="row.render" :s="data.a" side="a" /></div>
          <div class="cmp-col"><component :is="row.render" :s="data.b" side="b" /></div>
        </template>
      </div>

      <!-- 标签差异 -->
      <el-card shadow="never" class="diffbox">
        <div class="section-label">套路标签：共通 vs 各自特色</div>
        <div class="diff-row">
          <span class="diff-k">共通套路</span>
          <span class="diff-tags">
            <el-tag v-for="t in data.diff.shared_tags" :key="t" type="success" effect="light" round size="small">{{ t }}</el-tag>
            <span v-if="!data.diff.shared_tags.length" class="muted">（高频标签里暂无重合）</span>
          </span>
        </div>
        <div class="diff-row">
          <span class="diff-k">《{{ shortA }}》独有</span>
          <span class="diff-tags">
            <el-tag v-for="t in data.diff.only_a_tags" :key="t" effect="plain" round size="small">{{ t }}</el-tag>
          </span>
        </div>
        <div class="diff-row">
          <span class="diff-k">《{{ shortB }}》独有</span>
          <span class="diff-tags">
            <el-tag v-for="t in data.diff.only_b_tags" :key="t" effect="plain" round size="small" type="warning">{{ t }}</el-tag>
          </span>
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, h, onMounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElTag } from 'element-plus'
import { api } from '../api'

const loading = ref(true)
const books = ref([])
const idA = ref(null)
const idB = ref(null)
const data = ref(null)

const shortA = computed(() => (data.value?.a.title || '').slice(0, 6))
const shortB = computed(() => (data.value?.b.title || '').slice(0, 6))

// 渲染小工具:标签云 / 文本
const tagCloud = (key, type) => ({ s }) => h('div', { class: 'tag-row' },
  (s[key] || []).slice(0, 10).map(([t, n]) => h(ElTag, { size: 'small', round: true, effect: 'plain', type }, () => `${t} ${n}`)))
const plain = (key) => ({ s }) => h('div', {}, s[key] || '—')
const counts = () => ({ s }) => h('div', { class: 'muted' }, `做派卡 ${s.counts.behavior} · 对话卡 ${s.counts.dialogue} · 规则 ${s.counts.rules} · 人物 ${s.counts.characters}`)
const ruleCats = () => ({ s }) => h('div', { class: 'tag-row' },
  (s.rule_categories || []).map(([c, n]) => h(ElTag, { size: 'small', round: true, type: 'info' }, () => `${c} ${n}`)))
const chapters = () => ({ s }) => h('div', {}, `${s.analyzed_chapters} / ${s.total_chapters} 章`)
const pattern = () => ({ s }) => h('div', { style: 'line-height:1.7' }, s.protagonist_pattern || '—')

const rows = [
  { key: 'protagonist', label: '主角', render: plain('protagonist') },
  { key: 'setting', label: '题材', render: plain('setting') },
  { key: 'chapters', label: '已分析', render: chapters() },
  { key: 'pattern', label: '主角处世模式', render: pattern() },
  { key: 'tags', label: '高频套路标签', render: tagCloud('top_tags', 'info') },
  { key: 'scen', label: '高频对话场景', render: tagCloud('top_scenarios', 'primary') },
  { key: 'tech', label: '高频话术技巧', render: tagCloud('top_techniques', 'warning') },
  { key: 'cats', label: '规则侧重', render: ruleCats() },
  { key: 'counts', label: '数据量', render: counts() },
]

// 对比结论(示例书评已在开源版移除;可改为数据驱动或自行补充)
const verdict = computed(() => [])

// 优劣势/策略解读示例数据已在开源版移除(可按 book id 自行补充)
const bookLore = {}
const strategyRows = []
const lore12 = computed(() => false)
const loreA = computed(() => bookLore[data.value?.a.id] || { title: '', name: '', pros: [], cons: [] })
const loreB = computed(() => bookLore[data.value?.b.id] || { title: '', name: '', pros: [], cons: [] })

async function reload() {
  if (!idA.value || !idB.value) return
  loading.value = true
  try {
    const { data: d } = await api.compare(idA.value, idB.value)
    data.value = d
  } catch {
    ElMessage({ message: '加载对比数据失败,请稍后重试', type: 'error', grouping: true })
  } finally { loading.value = false }
}

onMounted(async () => {
  try {
    const { data: bs } = await api.listBooks()
    books.value = bs
    idA.value = bs[0]?.id
    idB.value = bs[1]?.id || bs[0]?.id
    await reload()
  } catch {
    ElMessage({ message: '加载对比数据失败,请稍后重试', type: 'error', grouping: true })
  } finally { loading.value = false }
})
</script>

<style scoped>
.bar-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.pickers { display: flex; align-items: center; gap: 16px; margin: 8px 0 20px; }
.vs { font-family: var(--font-display); font-weight: 700; color: var(--accent); }
.verdict { margin-bottom: 20px; }
.verdict ul { margin: 8px 0 0; padding-left: 18px; }
.verdict li { line-height: 1.9; }

.cmp-grid {
  display: grid;
  grid-template-columns: 130px 1fr 1fr;
  border: 1px solid var(--border); border-radius: 10px; overflow: hidden; background: var(--card);
}
.cmp-col { padding: 12px 16px; border-bottom: 1px solid var(--border); min-width: 0; overflow-wrap: anywhere; }
.cmp-grid > .cmp-col:nth-child(3n+2) { border-left: 1px solid var(--border); }
.cmp-grid > .cmp-col:nth-child(3n) { border-left: 1px solid var(--border); }
.cmp-head { background: var(--muted); font-family: var(--font-display); font-weight: 600; }
.cmp-head.book { font-size: 15px; }
.cmp-label { color: var(--muted-fg); font-size: 13px; font-weight: 600; background: var(--accent-subtle); }
.sw-sub.pros { color: var(--success); }
.sw-sub.cons { color: var(--danger); }
.sw-col ul { margin: 0; padding-left: 18px; }
.sw-col li { font-size: 14px; line-height: 1.75; color: var(--fg); margin: 2px 0; }

/* 手机:选择器堆叠 + 对照表列收窄不溢出 */
@media (max-width: 640px) {
  .bar-header { flex-wrap: wrap; gap: 8px; }
  .pickers { flex-direction: column; align-items: stretch; gap: 8px; }
  .pickers .el-select { width: 100% !important; }
  .vs { text-align: center; }
  .cmp-grid { grid-template-columns: 72px 1fr 1fr; }
  .cmp-col { padding: 10px 8px; font-size: 13px; }
  .cmp-head.book { font-size: 13px; }
}
</style>
