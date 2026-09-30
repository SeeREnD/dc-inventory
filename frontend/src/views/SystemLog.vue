<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-input v-model="query.username" placeholder="按用户名搜索" clearable style="width: 180px" @keyup.enter="onSearch" @clear="onSearch" />
      <el-select v-model="query.action" placeholder="操作类型" clearable style="width: 150px" @change="onSearch">
        <el-option v-for="a in ACTIONS" :key="a" :label="a" :value="a" />
      </el-select>
      <el-button type="primary" @click="onSearch">查询</el-button>
      <el-button @click="onReset">重置</el-button>
    </div>

    <el-table :data="items" v-loading="loading" stripe border>
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="username" label="用户名" width="130" />
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-tag :type="actionType(row.action)" size="small">{{ row.action }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="ip" label="IP" width="140">
        <template #default="{ row }">{{ row.ip || '-' }}</template>
      </el-table-column>
      <el-table-column label="详情" min-width="300">
        <template #default="{ row }">
          <span class="detail">{{ formatDetail(row) }}</span>
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
import { fmtTime } from '../constants/dicts'

const ACTIONS = [
  '登录成功', '登录失败', '退出登录', '修改密码',
  '创建用户', '修改用户', '创建备份', '回退数据', '删除备份', '修改备份保留时长'
]

const items = ref([])
const total = ref(0)
const loading = ref(false)
const query = reactive({ page: 1, page_size: 20, username: '', action: '' })

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/audit-logs', { params: { ...query } })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onSearch() { query.page = 1; load() }
function onReset() { Object.assign(query, { page: 1, username: '', action: '' }); load() }

function actionType(a) {
  if (a === '登录失败') return 'danger'
  if (a === '登录成功') return 'success'
  if (a.includes('备份') || a === '回退数据') return 'warning'
  return 'primary'
}

function formatDetail(row) {
  if (!row.detail) return '-'
  if (row.detail.reason) return `原因：${row.detail.reason}`
  return JSON.stringify(row.detail)
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.detail { font-size: 12px; color: #667085; word-break: break-all; }
</style>
