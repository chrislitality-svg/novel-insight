<template>
  <div class="page" v-loading="loading">
    <div class="bar-header">
      <div>
        <h2 class="page-title">社会规则 / 潜规则手册</h2>
        <p class="page-subtitle">这本书里"没人教就不懂"的社会运行规则，跨章提炼去重</p>
      </div>
      <el-button @click="$router.push(`/books/${id}`)" plain round size="small">
        <el-icon><ArrowLeft /></el-icon> 返回书籍
      </el-button>
    </div>

    <el-radio-group v-model="category" style="margin-bottom:20px" size="small">
      <el-radio-button value="">全部 ({{ rules.length }})</el-radio-button>
      <el-radio-button v-for="[c, n] in facets.categories" :key="c" :value="c">{{ c }} ({{ n }})</el-radio-button>
    </el-radio-group>

    <el-empty v-if="!loading && shown.length === 0" description="暂无规则手册" />

    <div class="rule-grid">
      <div v-for="r in shown" :key="r.id" class="rule-card">
        <div class="rule-cat">{{ r.category || '其他' }}</div>
        <p class="rule-text">{{ r.rule }}</p>
        <p v-if="r.explanation" class="rule-expl">{{ r.explanation }}</p>
        <div v-if="r.examples?.length" class="rule-chapters">
          <span class="muted">出处：</span>
          <span v-for="(e, i) in r.examples.slice(0, 5)" :key="i" class="ch-link">第{{ e.chapter_index }}章</span>
          <span v-if="r.examples.length > 5" class="muted">等 {{ r.occurrence }} 处</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const id = Number(props.id)

const loading = ref(true)
const rules = ref([])
const facets = ref({ categories: [] })
const category = ref('')

const shown = computed(() =>
  category.value ? rules.value.filter((r) => r.category === category.value) : rules.value
)

onMounted(async () => {
  try {
    const { data } = await api.listRules(id)
    rules.value = data.rules
    facets.value = data.facets
  } catch {
    ElMessage({ message: '加载规则手册失败,请稍后重试', type: 'error', grouping: true })
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.rule-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(440px, 100%), 1fr));
  gap: 16px;
  align-items: start;
}
.rule-card {
  border: 1px solid var(--border); border-left: 3px solid var(--accent);
  background: var(--card); border-radius: 6px;
  padding: 18px 22px;
  transition: border-color .12s;
}
.rule-card:hover { border-left-color: var(--accent-secondary, var(--accent)); }
.rule-cat {
  font-family: var(--font-mono); font-size: 11px; letter-spacing: .08em;
  color: var(--accent); text-transform: uppercase; margin-bottom: 8px;
}
.rule-text { font-size: 15px; font-weight: 600; line-height: 1.6; color: var(--fg); margin: 0 0 8px; }
.rule-expl { font-size: 13.5px; line-height: 1.75; color: var(--muted-fg); margin: 0 0 10px; }
.rule-chapters { font-size: 12px; color: var(--muted-fg); display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.ch-link { color: var(--accent); }
</style>
