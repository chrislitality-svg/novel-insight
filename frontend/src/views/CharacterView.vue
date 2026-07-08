<template>
  <div class="page" v-loading="loading">
    <div class="bar">
      <h2 class="page-title" style="margin:0">人物画像</h2>
      <el-button @click="$router.push(`/books/${id}`)" plain round size="small">
        <el-icon><ArrowLeft /></el-icon> 返回书籍
      </el-button>
    </div>

    <el-empty v-if="!loading && characters.length === 0" description="暂无人物画像(分析完成后自动生成)" />

    <div class="char-layout" v-if="characters.length">
      <aside class="char-side">
        <div
          v-for="c in characters"
          :key="c.id"
          class="char-item clickable"
          :class="{ active: current?.id === c.id }"
          @click="select(c)"
        >
          <span class="char-name">{{ c.name }}</span>
          <span class="char-role" :class="'role-' + (roleClass(c.role_type))">{{ c.role_type || '—' }}</span>
          <span class="char-count">{{ c.appearance_count }} 章</span>
        </div>
      </aside>

      <main class="char-main" v-if="current">
        <header class="char-head">
          <div>
            <h3 class="char-h-name">{{ current.name }}</h3>
            <span class="char-h-role" :class="'role-' + (roleClass(current.role_type))">{{ current.role_type || '—' }}</span>
          </div>
          <el-button text size="small" @click="exportChar">导出 →</el-button>
        </header>

        <p class="char-pattern" v-if="current.behavior_pattern">{{ current.behavior_pattern }}</p>

        <div class="scene-section" v-if="current.scenes?.length">
          <div class="scene-title">出场场景 · {{ current.scenes.length }} 个</div>
          <div class="scene-list">
            <div v-for="(s, i) in current.scenes" :key="i" class="scene-row">
              <span class="scene-ch">第{{ s.chapter_index }}章</span>
              <div class="scene-body">
                <p class="scene-text">{{ s.scene }}</p>
                <p v-if="s.lesson" class="scene-lesson">{{ s.lesson }}</p>
              </div>
            </div>
          </div>
        </div>
      </main>
      <main class="char-main empty" v-else>
        <el-empty description="选择左侧人物查看画像" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const props = defineProps({ id: { type: [String, Number], required: true }, cid: { type: [String, Number], default: null } })
const router = useRouter()
const id = Number(props.id)

const loading = ref(true)
const characters = ref([])
const current = ref(null)

function roleClass(r) { return { 主角: 'lead', 重要配角: 'major', 路人: 'minor' }[r] || 'other' }

async function select(c) {
  const { data } = await api.getCharacter(c.id)
  current.value = data
  router.replace(`/books/${id}/characters/${c.id}`)
}
function exportChar() {
  window.open(api.exportCharacterUrl(id, current.value.id), '_blank')
}

onMounted(async () => {
  try {
    const { data } = await api.listCharacters(id)
    characters.value = data
    const target = props.cid ? data.find((c) => c.id === Number(props.cid)) : data[0]
    if (target) await select(target)
  } catch {
    ElMessage({ message: '加载人物画像失败,请稍后重试', type: 'error', grouping: true })
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }

/* 两栏布局：左侧人物列表 + 右侧详情 */
.char-layout { display: grid; grid-template-columns: 240px 1fr; gap: 18px; align-items: start; }
.char-side {
  border: 1px solid var(--border); border-radius: 8px; background: var(--card);
  overflow: hidden; max-height: calc(100vh - 10rem); overflow-y: auto;
  position: sticky; top: 1rem;
}
.char-item {
  display: grid; grid-template-columns: 1fr auto auto; gap: 8px; align-items: center;
  padding: 12px 14px; border-bottom: 1px solid var(--border); cursor: pointer;
  transition: background-color .12s;
}
.char-item:last-child { border-bottom: none; }
.char-item:hover { background: var(--muted); }
.char-item.active { background: var(--accent-subtle); box-shadow: inset 3px 0 0 var(--accent); }
.char-name { font-size: 14px; font-weight: 600; color: var(--fg); }
.char-role {
  font-size: 10.5px; padding: 1px 7px; border-radius: 999px;
  font-family: var(--font-mono);
}
.char-role.role-lead { background: rgba(205, 138, 85, .15); color: #b96d2f; }
.char-role.role-major { background: rgba(200, 160, 100, .15); color: #8a6c3a; }
.char-role.role-minor { background: var(--muted); color: var(--muted-fg); }
.char-role.role-other { background: var(--muted); color: var(--muted-fg); }
.char-count { font-size: 11.5px; color: var(--muted-fg); font-family: var(--font-mono); }

/* 主区 */
.char-main {
  border: 1px solid var(--border); border-radius: 8px; background: var(--card);
  padding: 24px 28px;
}
.char-main.empty { padding: 60px 20px; }
.char-head {
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
  padding-bottom: 14px; margin-bottom: 18px; border-bottom: 1px solid var(--border);
}
.char-h-name { font-family: var(--font-display); font-size: 1.5rem; font-weight: 600; color: var(--fg); margin: 0 0 4px; }
.char-h-role {
  font-size: 11px; padding: 2px 9px; border-radius: 999px; font-family: var(--font-mono);
}
.char-h-role.role-lead { background: rgba(205, 138, 85, .15); color: #b96d2f; }
.char-h-role.role-major { background: rgba(200, 160, 100, .15); color: #8a6c3a; }
.char-h-role.role-minor { background: var(--muted); color: var(--muted-fg); }
.char-h-role.role-other { background: var(--muted); color: var(--muted-fg); }

.char-pattern {
  font-size: 15px; line-height: 1.85; color: var(--fg);
  background: var(--accent-subtle); border-left: 3px solid var(--accent);
  padding: 14px 18px; border-radius: 0 6px 6px 0; margin: 0 0 22px;
}

.scene-title {
  font-family: var(--font-display); font-size: 14.5px; font-weight: 600; color: var(--fg);
  margin-bottom: 12px;
}
.scene-list { display: flex; flex-direction: column; gap: 14px; }
.scene-row {
  display: grid; grid-template-columns: 70px 1fr; gap: 14px;
  padding-bottom: 14px; border-bottom: 1px dashed var(--border);
}
.scene-row:last-child { border-bottom: none; }
.scene-ch {
  font-family: var(--font-mono); font-size: 12px; color: var(--accent); font-weight: 600;
  padding-top: 2px;
}
.scene-body { min-width: 0; }
.scene-text { font-size: 14px; line-height: 1.75; color: var(--fg); margin: 0; }
.scene-lesson {
  font-size: 13px; line-height: 1.7; color: var(--muted-fg); margin: 6px 0 0;
  padding-left: 10px; border-left: 2px solid var(--border);
}

@media (max-width: 900px) {
  .char-layout { grid-template-columns: 1fr; }
  .char-side { max-height: 280px; position: static; }
}
</style>
