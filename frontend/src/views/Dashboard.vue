<template>
  <div v-loading="loading">
    <el-row :gutter="16">
      <el-col :span="6" v-for="card in cards" :key="card.title">
        <el-card shadow="never" class="stat-card" :body-style="{ padding: '16px 20px' }" @click="card.onClick">
          <div class="stat-title">{{ card.title }}</div>
          <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="8">
        <el-card shadow="never"><div ref="statusChart" style="height: 300px" /></el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never"><div ref="categoryChart" style="height: 300px" /></el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never"><div ref="roomChart" style="height: 300px" /></el-card>
      </el-col>
    </el-row>
    <div class="hint">提示：点击图表可跳转到设备台账并自动筛选</div>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="section-header">
          <span>30 天内过保设备</span>
          <el-tag type="warning" size="small" v-if="stats.expiring_warranty?.length">{{ stats.expiring_warranty.length }} 台</el-tag>
        </div>
      </template>
      <el-table :data="stats.expiring_warranty || []" stripe border>
        <el-table-column prop="asset_no" label="资产编号" width="140" />
        <el-table-column prop="name" label="设备名称" min-width="140" />
        <el-table-column prop="room_name" label="机房" width="120" />
        <el-table-column prop="warranty_end" label="保修到期" width="120" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import api from '../api'

const router = useRouter()
const loading = ref(false)
const stats = ref({})
const rooms = ref([])
const statusChart = ref(null)
const categoryChart = ref(null)
const roomChart = ref(null)
let charts = []

const cards = computed(() => [
  { title: '设备总数', value: stats.value.total ?? 0, color: '#409eff',
    onClick: () => router.push('/equipment') },
  { title: '在用设备', value: stats.value.by_status?.在用 ?? 0, color: '#67c23a',
    onClick: () => router.push({ path: '/equipment', query: { status: '在用' } }) },
  { title: '维修中', value: stats.value.by_status?.维修 ?? 0, color: '#e6a23c',
    onClick: () => router.push({ path: '/equipment', query: { status: '维修' } }) },
  { title: '30天内过保', value: stats.value.expiring_warranty?.length ?? 0, color: '#f56c6c',
    onClick: () => {} }
])

async function load() {
  loading.value = true
  try {
    stats.value = (await api.get('/stats')).data
    renderCharts()
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  charts.forEach((c) => c.dispose())
  charts = []

  const statusInst = echarts.init(statusChart.value)
  statusInst.setOption({
    title: { text: '设备状态分布', left: 'center' },
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['35%', '62%'], center: ['50%', '48%'],
      data: Object.entries(stats.value.by_status || {}).map(([name, value]) => ({ name, value }))
    }]
  })
  statusInst.on('click', (p) =>
    router.push({ path: '/equipment', query: { status: p.name } })
  )

  const catInst = echarts.init(categoryChart.value)
  catInst.setOption({
    title: { text: '设备类型分布', left: 'center' },
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['35%', '62%'], center: ['50%', '48%'],
      data: Object.entries(stats.value.by_category || {}).map(([name, value]) => ({ name, value }))
    }]
  })
  catInst.on('click', (p) =>
    router.push({ path: '/equipment', query: { category: p.name } })
  )

  const roomInst = echarts.init(roomChart.value)
  const roomEntries = Object.entries(stats.value.by_room || {})
  roomInst.setOption({
    title: { text: '各机房设备数量', left: 'center' },
    tooltip: { trigger: 'axis' },
    grid: { bottom: 70 },
    xAxis: { type: 'category', data: roomEntries.map(([k]) => k), axisLabel: { rotate: 20 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{ type: 'bar', data: roomEntries.map(([, v]) => v), barMaxWidth: 36, itemStyle: { color: '#409eff', borderRadius: [4, 4, 0, 0] } }]
  })
  roomInst.on('click', (p) => {
    const room = rooms.value.find((r) => r.name === p.name)
    if (room) router.push({ path: '/equipment', query: { room_id: room.id } })
  })

  charts = [statusInst, catInst, roomInst]
}

function onResize() {
  charts.forEach((c) => c.resize())
}

onMounted(async () => {
  rooms.value = (await api.get('/rooms')).data
  load()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  charts.forEach((c) => c.dispose())
})
</script>

<style scoped>
.stat-card { cursor: pointer; transition: box-shadow 0.2s; }
.stat-card:hover { box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12); }
.stat-title { font-size: 13px; color: #909399; }
.stat-value { font-size: 30px; font-weight: 700; margin-top: 6px; }
.hint { font-size: 12px; color: #c0c4cc; margin-top: 8px; text-align: center; }
.section-header { display: flex; align-items: center; gap: 8px; }
</style>
