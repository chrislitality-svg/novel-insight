<template>
  <div class="page" v-loading="loading">
    <div class="bar-header">
      <div>
        <h2 class="page-title">家庭 · 人情世故</h2>
        <p class="page-subtitle">这本书里关于婚恋与家庭的处世规则——观点、背后的理念、以及主角的处理方式，按主题归类</p>
      </div>
      <el-button @click="$router.push(`/books/${id}`)" plain round size="small">
        <el-icon><ArrowLeft /></el-icon> 返回书籍
      </el-button>
    </div>

    <!-- 理念总览：规则手册中的家庭沉淀规则 -->
    <el-collapse v-if="data.handbook.length" v-model="hbOpen" style="margin:4px 0 18px">
      <el-collapse-item name="hb">
        <template #title>
          <span class="hb-title">理念总览 · 跨章沉淀的家庭规则（{{ data.handbook.length }}）</span>
        </template>
        <div class="hb-grid">
          <div v-for="r in data.handbook" :key="r.id" class="hb-item">
            <div class="fam-row">
              <span class="chip chip-gold">{{ r.category || '婚恋家庭' }}</span>
              <span class="muted">出现 {{ r.occurrence }} 次</span>
            </div>
            <p class="fam-rule" style="margin:8px 0 4px">{{ r.rule }}</p>
            <div v-if="r.explanation" class="muted" style="line-height:1.7">{{ r.explanation }}</div>
            <div v-if="r.examples?.length" class="fam-row" style="margin-top:8px">
              <span v-for="(e, i) in r.examples.slice(0, 8)" :key="i" class="chip chip-plain">第{{ e.chapter_index }}章</span>
            </div>
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>

    <!-- 筛选 -->
    <div class="fam-controls" v-if="!loading && data.total">
      <el-radio-group v-model="theme" size="small">
        <el-radio-button value="">全部 ({{ data.total }})</el-radio-button>
        <el-radio-button v-for="t in data.themes" :key="t.name" :value="t.name">
          {{ t.name }} ({{ t.count }})
        </el-radio-button>
      </el-radio-group>
      <el-switch v-model="onlyTag" size="small" active-text="只看标签精选" style="margin-left:auto" />
    </div>

    <el-empty v-if="!loading && data.total === 0" description="本书暂无家庭相关的人情世故" />

    <!-- 逐条规则，按主题分组（轻量卡片，分批渲染） -->
    <div v-for="t in shownThemes" :key="t.name" class="theme-block">
      <div class="theme-head">
        <span class="theme-name">{{ t.name }}</span>
        <span class="muted">{{ t.shownItems.length }} 条</span>
      </div>
      <div class="fam-grid">
        <div v-for="it in t.shownItems.slice(0, limitFor(t.name))" :key="it.chapter_id + '-' + it.rule.slice(0, 10)" class="fam-card">
          <p class="fam-rule">{{ it.rule }}</p>
          <p v-if="it.why" class="fam-why">{{ it.why }}</p>
          <div class="fam-source muted">第{{ it.chapter_index }}章 · {{ it.chapter_title }}</div>
        </div>
      </div>
      <div v-if="t.shownItems.length > limitFor(t.name)" class="fam-more">
        <el-button text type="primary" @click="expand(t.name)">展开剩余 {{ t.shownItems.length - limitFor(t.name) }} 条 ↓</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const id = Number(props.id)
const PAGE = 24

const loading = ref(true)
const data = ref({ total: 0, tag_count: 0, keyword_count: 0, themes: [], handbook: [] })
const theme = ref('')
const onlyTag = ref(false)
const hbOpen = ref([])
const limits = reactive({})

const shownThemes = computed(() =>
  data.value.themes
    .filter((t) => !theme.value || t.name === theme.value)
    .map((t) => ({
      ...t,
      shownItems: onlyTag.value ? t.items.filter((it) => it.source === 'tag') : t.items,
    }))
    .filter((t) => t.shownItems.length)
)

function limitFor(name) { return limits[name] ?? PAGE }
function expand(name) { limits[name] = (limits[name] ?? PAGE) + 200 }

// 切换筛选时重置分批，避免一次性渲染过多卡片
watch([theme, onlyTag], () => { for (const k of Object.keys(limits)) delete limits[k] })

onMounted(async () => {
  try {
    const { data: d } = await api.familyInsights(id)
    data.value = d
  } catch {
    ElMessage({ message: '加载家庭洞察失败,请稍后重试', type: 'error', grouping: true })
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.hb-title { font-weight: 600; color: var(--fg); }
.hb-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(440px, 100%), 1fr)); gap: 14px; }
.hb-item { border: 1px solid var(--border); border-radius: 8px; background: var(--muted); padding: 16px 18px; }
.hb-item .fam-row { display: flex; align-items: center; justify-content: space-between; gap: 6px; flex-wrap: wrap; }
.hb-item .fam-rule { font-size: 14.5px; font-weight: 600; line-height: 1.6; color: var(--fg); margin: 8px 0 4px; }

.fam-controls { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }

.theme-block { margin-bottom: 28px; }
.theme-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.theme-name { font-family: var(--font-display); font-size: 1.05rem; font-weight: 600; color: var(--fg); }

/* 简化卡片：只保留 规则 + 理念 + 出处 */
.fam-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(440px, 100%), 1fr));
  gap: 14px;
  align-items: start;
}
.fam-card {
  border: 1px solid var(--border); border-left: 3px solid var(--accent);
  border-radius: 6px; background: var(--card);
  padding: 18px 22px;
  transition: border-color .12s;
}
.fam-card:hover { border-left-color: var(--accent-secondary, var(--accent)); }
.fam-rule { font-size: 15px; font-weight: 600; line-height: 1.6; color: var(--fg); margin: 0 0 10px; }
.fam-why { font-size: 13.5px; line-height: 1.75; color: var(--muted-fg); margin: 0; }
.fam-source { margin-top: 12px; padding-top: 10px; border-top: 1px dashed var(--border); font-size: 12px; }

.fam-more { text-align: center; margin: 4px 0 10px; }

/* chips（仅 hb-item 还在用） */
.chip { display: inline-block; padding: 1px 9px; border-radius: 999px; font-size: .72rem; line-height: 1.7; white-space: nowrap; }
.chip-gold { background: var(--accent); color: #fff; }
.chip-plain { background: var(--muted); color: var(--muted-fg); border: 1px solid var(--border); }
</style>
