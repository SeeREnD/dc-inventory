<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-button type="primary" :loading="creating" @click="createBackup">立即创建备份</el-button>
      <div style="flex: 1" />
      <span style="color: #909399; font-size: 13px; align-self: center">自动备份保留</span>
      <el-input-number v-model="retention" :min="1" :max="365" size="default" style="width: 110px" />
      <span style="color: #909399; font-size: 13px; align-self: center">天</span>
      <el-button :loading="savingRetention" @click="saveRetention">保存设置</el-button>
    </div>

    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      系统每天自动备份一次数据库，并按保留天数自动清理旧备份。回退操作会先把当前数据自动另存为安全快照（"回退前自动"），再恢复到所选版本。
    </el-alert>

    <el-table :data="backups" v-loading="loading" stripe border>
      <el-table-column prop="name" label="备份文件" min-width="280" show-overflow-tooltip />
      <el-table-column label="类型" width="110">
        <template #default="{ row }">
          <el-tag :type="row.kind === '手动' ? 'primary' : row.kind === '每日自动' ? 'success' : 'warning'" size="small">
            {{ row.kind }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ formatSize(row.size) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="210" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="download(row)">下载</el-button>
          <el-button link type="warning" @click="restore(row)">回退到此版本</el-button>
          <el-popconfirm title="确认删除该备份？" @confirm="del(row)">
            <template #reference>
              <el-button link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无备份，点击左上角「立即创建备份」" :image-size="80" />
      </template>
    </el-table>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const backups = ref([])
const loading = ref(false)
const creating = ref(false)
const retention = ref(7)
const savingRetention = ref(false)

async function load() {
  loading.value = true
  try {
    backups.value = (await api.get('/backups')).data
  } finally {
    loading.value = false
  }
}

async function loadRetention() {
  const { data } = await api.get('/backups/settings/retention')
  retention.value = data.retention_days
}

async function saveRetention() {
  savingRetention.value = true
  try {
    await api.put('/backups/settings/retention', { retention_days: retention.value })
    ElMessage.success(`已设置保留 ${retention.value} 天，超期备份已清理`)
    load()
  } finally {
    savingRetention.value = false
  }
}

async function createBackup() {
  creating.value = true
  try {
    await api.post('/backups')
    ElMessage.success('备份已创建')
    load()
  } finally {
    creating.value = false
  }
}

async function download(row) {
  const res = await api.get(`/backups/${row.name}/download`, { responseType: 'blob' })
  const blobUrl = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = row.name
  a.click()
  URL.revokeObjectURL(blobUrl)
}

async function restore(row) {
  try {
    await ElMessageBox.confirm(
      `确认将数据回退到「${row.created_at}」的版本？\n当前数据会先自动保存为安全快照，之后可从快照再回退回来。`,
      '回退数据',
      { type: 'warning', confirmButtonText: '回退', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  await api.post(`/backups/${row.name}/restore`)
  ElMessage.success('已回退，请刷新页面查看最新数据')
  load()
}

async function del(row) {
  await api.delete(`/backups/${row.name}`)
  ElMessage.success('已删除')
  load()
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

onMounted(() => {
  load()
  loadRetention()
})
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
</style>
