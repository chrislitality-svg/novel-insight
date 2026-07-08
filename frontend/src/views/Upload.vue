<template>
  <div class="page">
    <h2 class="page-title">投入一本网络小说</h2>
    <p class="page-subtitle">支持单文件(.txt / .epub,自动切分),或指向一个已按章切好的文件夹(每个 txt = 一章)</p>

    <el-tabs v-model="mode">
      <el-tab-pane label="上传单个文件" name="file">
        <el-upload
          drag
          :auto-upload="false"
          :show-file-list="true"
          :limit="1"
          accept=".txt,.epub"
          :on-change="onFileChange"
          :on-exceed="onExceed"
          ref="uploadRef"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">把书拖到这里，或 <em>点击选择</em></div>
        </el-upload>
        <div style="margin-top: 16px">
          <el-button type="primary" :loading="uploading" :disabled="!file" @click="doUpload">
            {{ uploading ? '切分中…' : '上传并切分' }}
          </el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="从文件夹导入(已分章)" name="folder">
        <el-form label-width="90px" style="max-width: 720px">
          <el-form-item label="文件夹路径">
            <el-input v-model="folderPath" placeholder="如 C:\Users\hycst\novel_dl\书名" clearable />
          </el-form-item>
          <el-form-item label="书名(可选)">
            <el-input v-model="folderTitle" placeholder="留空则用文件夹名" clearable />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="uploading" :disabled="!folderPath" @click="doImportFolder">
              {{ uploading ? '导入中…' : '按文件名顺序导入' }}
            </el-button>
            <span class="muted" style="margin-left:12px">每个 .txt 文件作为一章，首行作标题</span>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <el-card v-if="result" style="margin-top: 24px">
      <template #header>
        <b>《{{ result.title }}》切分完成</b>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="总章节">{{ result.total_chapters }}</el-descriptions-item>
        <el-descriptions-item label="待分析章节">{{ result.analyzable_chapters }}</el-descriptions-item>
        <el-descriptions-item label="平均字数">{{ result.avg_char_count }}</el-descriptions-item>
      </el-descriptions>

      <h4>事件密度分布</h4>
      <div class="histo">
        <div v-for="(v, k) in result.density_histogram" :key="k" class="histo-col">
          <div class="histo-bar" :style="{ height: barHeight(v) + 'px' }" :title="`${k}: ${v} 章`"></div>
          <div class="histo-label">{{ k }}</div>
          <div class="histo-count">{{ v }}</div>
        </div>
      </div>

      <div style="margin-top: 16px; display: flex; gap: 12px">
        <el-button type="primary" @click="startAnalyze">一键启动分析</el-button>
        <el-button @click="$router.push(`/books/${result.id}`)">先看章节</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const router = useRouter()
const mode = ref('file')
const file = ref(null)
const folderPath = ref('')
const folderTitle = ref('')
const uploading = ref(false)
const result = ref(null)
const uploadRef = ref()

function onFileChange(f) { file.value = f.raw }
function onExceed(files) {
  uploadRef.value.clearFiles()
  uploadRef.value.handleStart(files[0])
  file.value = files[0]
}

const maxCount = () => Math.max(1, ...Object.values(result.value?.density_histogram || { a: 1 }))
function barHeight(v) { return Math.round((v / maxCount()) * 120) + 2 }

async function doUpload() {
  if (!file.value) return
  uploading.value = true
  try {
    const { data } = await api.uploadBook(file.value)
    result.value = data
    ElMessage.success('切分完成')
  } catch (e) {
    ElMessage.error('上传失败:' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
  }
}

async function doImportFolder() {
  if (!folderPath.value) return
  uploading.value = true
  try {
    const { data } = await api.importFolder(folderPath.value, folderTitle.value || null)
    result.value = data
    ElMessage.success(`导入完成,共 ${data.total_chapters} 章`)
  } catch (e) {
    ElMessage.error('导入失败:' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
  }
}

async function startAnalyze() {
  try {
    await api.startAnalyze(result.value.id)
    ElMessage.success('已启动分析')
    router.push(`/books/${result.value.id}`)
  } catch (e) {
    ElMessage.error('启动失败:' + (e.response?.data?.detail || e.message))
  }
}
</script>

<style scoped>
.histo { display: flex; align-items: flex-end; gap: 6px; height: 160px; padding: 12px 0; border-bottom: 1px solid var(--border); }
.histo-col { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; flex: 1; }
.histo-bar { width: 70%; background: var(--accent); border-radius: 2px 2px 0 0; }
.histo-label { font-size: 11px; color: var(--muted-fg); margin-top: 4px; transform: rotate(-30deg); white-space: nowrap; }
.histo-count { font-size: 12px; color: var(--fg); }
</style>
