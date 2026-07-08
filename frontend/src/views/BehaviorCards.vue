<template>
  <div class="page" v-loading="loading">
    <div class="bar-header">
      <div>
        <h2 class="page-title">处世策略</h2>
        <p class="page-subtitle">书里教的做人道理，拿到现实中直接用</p>
      </div>
      <el-button @click="$router.push(`/books/${id}`)" plain round size="small">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
    </div>

    <!-- 顶部横向 chip 筛选栏：默认显示 TOP 标签，超出自动折叠到"更多" -->
    <div class="filter-bar">
      <div class="filter-row">
        <span class="filter-label">标签</span>
        <div class="chip-wrap" :class="{ collapsed: !tagsExpanded }">
          <button class="chip" :class="{ active: !tag }" @click="tag = ''; reload()">全部</button>
          <button v-for="[t, n] in facets.tags" :key="t" class="chip"
            :class="{ active: tag === t }" @click="tag = t; reload()">
            {{ t }} <span class="chip-n">{{ n }}</span>
          </button>
        </div>
        <button v-if="facets.tags && facets.tags.length > 14" class="more-btn" @click="tagsExpanded = !tagsExpanded">
          {{ tagsExpanded ? '收起 ▴' : '更多 ▾' }}
        </button>
      </div>
      <div class="filter-row" v-if="facets.characters && facets.characters.length">
        <span class="filter-label">人物</span>
        <el-select v-model="character" placeholder="全部人物" clearable size="small" style="width:200px" @change="reload">
          <el-option v-for="[c, n] in facets.characters" :key="c" :value="c" :label="`${c} (${n})`" />
        </el-select>
        <el-button v-if="tag" size="small" type="success" plain round @click="exportTag" style="margin-left:auto">
          导出「{{ tag }}」
        </el-button>
      </div>
    </div>

    <div class="list-head">
      <span class="muted">共 <b>{{ shown.length }}</b> 条策略</span>
      <el-pagination v-if="shown.length > pageSize" size="small" background
        layout="prev, pager, next" :total="shown.length" :page-size="pageSize"
        v-model:current-page="page" @current-change="toTop" />
    </div>
    <el-empty v-if="!loading && shown.length === 0" description="暂无处世策略" />

    <div class="bh-grid">
      <div v-for="c in paged" :key="c.id" class="grid-item">
        <el-card shadow="hover" :body-style="{ padding: 0 }">

          <!-- 场景标题 -->
          <div class="bh-top">
            <span class="card-chapter-badge">{{ c.chapter_index }} · {{ c.chapter_title }}</span>
            <div class="rule-accent" style="margin:.5rem 0"></div>
            <p class="bh-scene">{{ c.scene_summary }}</p>
            <div class="bh-chars" v-if="c.characters_involved?.length">
              <el-tag v-for="n in c.characters_involved" :key="n" size="small" round>{{ n }}</el-tag>
            </div>
          </div>

          <!-- 处世原则 -->
          <div class="bh-analysis" v-if="c.freeform_analysis">
            <div class="bh-text">{{ c.freeform_analysis }}</div>
          </div>

          <!-- 社会规则 -->
          <div v-if="c.social_rules?.length" class="rules-box" style="margin:.5rem 1.5rem">
            <b>社会规则</b>
            <div class="rule-accent" style="margin:.375rem 0;height:1px;width:2rem;background:var(--border)"></div>
            <div v-for="(r, i) in c.social_rules" :key="i" class="rule-item">
              · {{ r.rule }}<span v-if="r.why" class="muted"> — {{ r.why }}</span>
            </div>
          </div>

          <!-- 核心道理 -->
          <div class="bh-lesson" v-if="c.core_lesson">
            <span class="section-label" style="display:inline;margin-right:.5rem">核心道理</span>
            {{ c.core_lesson }}
          </div>

          <!-- 标签 -->
          <div class="bh-tags">
            <el-tag v-for="t in c.tags" :key="t" type="info" size="small" round class="tag-click" @click="tag = t; reload()">{{ t }}</el-tag>
            <el-button text size="small" style="margin-left:auto;color:var(--accent)" @click="$router.push(`/books/${id}/read?cid=${c.chapter_id}`)">
              读原文 →
            </el-button>
          </div>

        </el-card>
      </div>
    </div>

    <div class="list-foot" v-if="shown.length > pageSize">
      <el-pagination background layout="prev, pager, next, jumper, total"
        :total="shown.length" :page-size="pageSize"
        v-model:current-page="page" @current-change="toTop" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true } })
const id = Number(props.id)

const loading = ref(true)
const cards = ref([])
const facets = ref({ tags: [], characters: [] })
const tag = ref('')
const character = ref('')
const page = ref(1)
const pageSize = 30
const tagsExpanded = ref(false)

const shown = computed(() => {
  let list = cards.value
  if (character.value) list = list.filter(c => (c.characters_involved || []).includes(character.value))
  return list
})
const paged = computed(() => shown.value.slice((page.value - 1) * pageSize, page.value * pageSize))

watch(character, () => { page.value = 1 })
function toTop() { window.scrollTo({ top: 0, behavior: 'smooth' }) }

async function reload() {
  loading.value = true
  page.value = 1
  try {
    const { data } = await api.behaviorCards(id, tag.value ? { tag: tag.value } : {})
    cards.value = data.cards
    facets.value = data.facets
  } catch {
    ElMessage({ message: '加载处世策略失败,请稍后重试', type: 'error', grouping: true })
  } finally { loading.value = false }
}
function exportTag() { window.open(api.exportTagUrl(id, tag.value), '_blank') }
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
/* 从左到右铺满横向的卡片栅格(取代纵向多列瀑布) */
.bh-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(340px, 100%), 1fr));
  gap: 1.25rem;
  align-items: start;
}
</style>
