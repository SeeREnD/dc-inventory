<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-select v-model="query.action" placeholder="操作类型" clearable style="width: 130px" @change="load">
        <el-option v-for="a in ['新增', '编辑', '删除', '导入']" :key="a" :label="a" :value="a" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
    </div>

    <el-table :data="items" v-loading="loading" stripe border>
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="asset_no" label="资产编号" width="130" />
      <el-table-column prop="action" label="操作" width="90">
        <template #default="{ row }">
          <el-tag :type="actionType(row.action)" size="small">{{ row.action }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="operator" label="操作人" width="110" />
      <el-table-column label="详情" min-width="360">
        <template #default="{ row }">
          <span class="log-detail">{{ formatDetail(row) }}</span>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="query.page"
      v-model:page-size="query.page_size"
      :total="total"
      :page-sizes="[20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      style="margin-top: 12px; justify-content: flex-end"
      @size-change="load"
      @current-change="load"
    />
  </el-card>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import api from '../api'

const items = ref([])
const total = ref(0)
const loading = ref(false)
const query = reactive({ page: 1, page_size: 20, action: '' })

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/changes', { params: { ...query } })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function fmtTime(t) {
  return t ? new Date(t).toLocaleString('zh-CN') : ''
}

function actionType(a) {
  return { 新增: 'success', 编辑: 'primary', 删除: 'danger', 导入: 'warning' }[a] || 'info'
}

function formatDetail(row) {
  if (!row.detail) return ''
  if (row.action === '编辑') {
    return Object.entries(row.detail)
      .map(([k, v]) => `${k}: ${JSON.stringify(v.old)} → ${JSON.stringify(v.new)}`)
      .join('；')
  }
  return JSON.stringify(row.detail)
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.log-detail {
  font-size: 12px;
  color: #667085;
  word-break: break-all;
}
</style>
