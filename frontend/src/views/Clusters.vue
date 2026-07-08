<template>
  <div class="page" v-loading="loading">
    <div class="bar-header">
      <div>
        <h2 class="page-title">情境聚类 & 长期账</h2>
        <p class="page-subtitle">每一类反复出现的情境：先看「共性打法」(观点)，再看「案例出处」(原文)</p>
      </div>
      <el-button @click="$router.push(`/books/${id}`)" plain round size="small">
        <el-icon><ArrowLeft /></el-icon> 返回书籍
      </el-button>
    </div>

    <!-- 长期账时间线 -->
    <el-card v-if="timeline && timeline.timeline?.length" shadow="never" class="tally-card" :body-style="{ padding: '18px 22px' }">
      <div class="section-label">人情债时间线</div>
      <p v-if="timeline.summary" class="tally-summary">{{ timeline.summary }}</p>
      <el-timeline style="margin-top:10px">
        <el-timeline-item
          v-for="(it, i) in timeline.timeline"
          :key="i"
          :timestamp="`第${it.chapter_index}章`"
          :type="isPaid(it.status) ? 'success' : 'warning'"
          placement="top"
        >
          <div class="tally-event">{{ it.event }}</div>
          <div class="muted" style="margin-top:2px">
            <el-tag size="small" :type="isPaid(it.status) ? 'success' : 'warning'" effect="plain" round>{{ it.status }}</el-tag>
            {{ it.payoff_note }}
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <div class="section-label" style="margin-top:6px">情境聚类（{{ clusters.length }} 类）</div>
    <el-empty v-if="!loading && clusters.length === 0" description="暂无情境聚类(分析完成后自动生成)" />

    <div class="cluster-grid">
      <el-card v-for="c in clusters" :key="c.id" shadow="hover" class="cluster-card" :body-style="{ padding: 0 }">
        <!-- 观点区:共性打法 = 重点 -->
        <div class="pattern-hero">
          <div class="cluster-name-row">
            <span class="cluster-name">{{ c.cluster_name }}</span>
            <span class="muted ex-count">{{ c.instance_count }} 例</span>
          </div>
          <div v-if="c.pattern_summary" class="pattern-bullets">
            <p v-for="(line, i) in splitSentences(c.pattern_summary)" :key="i" class="pattern-line">{{ line }}</p>
          </div>
          <p v-else class="pattern-empty muted">（暂无共性总结）</p>
        </div>

        <!-- 案例区:与观点分开 -->
        <div class="case-zone">
          <div class="case-toggle clickable" @click="toggle(c)">
            <span>案例 · 出处（{{ c.instance_count }}）</span>
            <span class="caret">{{ open[c.id] ? '收起 ▴' : '展开 ▾' }}</span>
          </div>
          <div v-show="open[c.id]" class="case-list">
            <template v-if="details[c.id]">
              <div v-for="(ins, i) in details[c.id].instances" :key="i" class="case-item">
                <span class="case-ch">第{{ ins.chapter_index }}章</span>
                <span class="case-text">{{ ins.summary }}</span>
              </div>
            </template>
            <div v-else class="muted" style="padding:10px 0">加载中…</div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const id = Number(props.id)

const loading = ref(true)
const clusters = ref([])
const timeline = ref(null)
const details = ref({})
const open = reactive({})

const isPaid = (s) => !!s && s.includes('已')

// 把长段落按句号/分号拆成短句，每句一行
function splitSentences(text) {
  if (!text) return []
  return text
    .split(/(?<=[。；])/g)
    .map(s => s.trim())
    .filter(s => s.length > 0)
}

async function loadInstances(c) {
  if (details.value[c.id]) return
  const { data } = await api.getCluster(c.id)
  details.value = { ...details.value, [c.id]: data }
}
function toggle(c) {
  open[c.id] = !open[c.id]
  if (open[c.id]) loadInstances(c)
}

onMounted(async () => {
  try {
    const [cl, tl] = await Promise.all([api.listClusters(id), api.tallyTimeline(id)])
    clusters.value = cl.data
    timeline.value = tl.data
  } catch {
    ElMessage({ message: '加载情境聚类失败,请稍后重试', type: 'error', grouping: true })
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.bar-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }

.tally-card { margin-bottom: 22px; }
.tally-summary { font-size: 15px; line-height: 1.8; color: var(--fg); margin: 6px 0 0; }
.tally-event { font-weight: 600; }

/* 横向栅格：每行 2 列，单卡可舒展 */
.cluster-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(480px, 100%), 1fr));
  gap: 1.25rem;
  align-items: start;
  margin-top: 12px;
}

/* 观点区:重点 —— 加重粗体、加 accent 左条 */
.pattern-hero { padding: 20px 22px 18px; border-left: 4px solid var(--accent); }
.cluster-name-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.cluster-name { font-family: var(--font-display); font-size: 17px; font-weight: 600; color: var(--fg); }
.ex-count { font-size: 12px; }
.pattern-bullets { display: flex; flex-direction: column; gap: 8px; }
.pattern-line {
  margin: 0;
  font-family: var(--font-body);
  font-size: 14.5px; line-height: 1.75; color: var(--fg);
  padding-left: 12px; position: relative;
}
.pattern-line::before {
  content: ''; position: absolute; left: 0; top: 0.7em;
  width: 4px; height: 4px; border-radius: 50%; background: var(--accent);
}
.pattern-empty { font-size: 13px; }
.case-zone { border-top: 1px solid var(--border); background: var(--accent-subtle); }
.case-toggle {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 20px; font-size: 13px; color: var(--muted-fg); user-select: none;
}
.case-toggle:hover { color: var(--accent); }
.caret { color: var(--accent); }
.case-list { padding: 0 20px 12px; }
.case-item {
  display: flex; gap: 10px; align-items: baseline;
  padding: 8px 0; border-bottom: 1px dashed var(--border); font-size: 14px; line-height: 1.6;
}
.case-item:last-child { border-bottom: none; }
.case-ch { color: var(--accent); font-weight: 600; flex-shrink: 0; font-size: 13px; }
.case-text { color: var(--fg); }
</style>
