<template>
  <el-card shadow="never">
    <!-- 选择栏 -->
    <div class="toolbar">
      <el-select v-model="roomId" placeholder="选择机房" style="width: 160px" @change="onRoomChange">
        <el-option v-for="r in rooms" :key="r.id" :label="r.name" :value="r.id" />
      </el-select>
      <el-select v-model="cabinetId" placeholder="选择机柜" clearable style="width: 160px" :disabled="!roomId" @change="loadDevices">
        <el-option v-for="c in cabinetsOfRoom" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <div style="flex: 1" />
      <!-- 图例 -->
      <div class="legend">
        <span v-for="c in CATEGORY" :key="c" class="legend-item">
          <i class="legend-dot" :style="{ background: CATEGORY_COLOR[c] }" />{{ c }}
        </span>
      </div>
    </div>

    <!-- 机房总览（未选机柜时） -->
    <template v-if="!cabinetId">
      <el-empty v-if="!roomId" description="请先选择机房和机柜" :image-size="100" />
      <el-empty v-else-if="!cabinetsOfRoom.length" description="该机房下暂无机柜，请先在「机房机柜」页创建" :image-size="100" />
      <el-row v-else :gutter="16">
        <el-col :span="6" v-for="c in cabinetsOfRoom" :key="c.id" style="margin-bottom: 16px">
          <el-card shadow="hover" class="cab-card" @click="cabinetId = c.id; loadDevices()">
            <div class="cab-name">{{ c.name }}</div>
            <div class="cab-usage">{{ usedU(c) }} / {{ c.capacity_u }} U 已用</div>
            <el-progress
              :percentage="c.capacity_u ? Math.round(usedU(c) / c.capacity_u * 100) : 0"
              :stroke-width="10"
              :color="usageColor(usedU(c) / c.capacity_u)"
            />
          </el-card>
        </el-col>
      </el-row>
    </template>

    <!-- 机架图 -->
    <template v-else>
      <div v-loading="loading" class="rack-layout">
        <div class="rack-info">
          <div class="rack-title">{{ currentRoomName }} / {{ currentCabinet?.name }}</div>
          <div class="rack-sub">
            容量 {{ currentCabinet?.capacity_u }}U · 已用 {{ usedUCount }}U · 剩余 {{ (currentCabinet?.capacity_u || 0) - usedUCount }}U
          </div>
        </div>

        <div class="rack-scroll">
          <div class="rack">
            <template v-for="row in rackRows" :key="row.u">
              <div class="u-label">{{ row.u }}</div>
              <div
                v-if="row.device && row.isTop"
                class="u-slot device"
                :style="{ height: row.span * U_HEIGHT - 2 + 'px', background: CATEGORY_COLOR[row.device.category] || '#909399' }"
                @click="openDetail(row.device)"
              >
                <div class="dev-name">{{ row.device.name }}</div>
                <div class="dev-asset">{{ row.device.asset_no }}</div>
              </div>
              <div v-else-if="row.device" class="u-slot covered" :style="{ background: 'transparent' }" />
              <div v-else class="u-slot empty" />
            </template>
          </div>
        </div>

        <!-- 未上架设备 -->
        <el-card v-if="unplaced.length" shadow="never" class="unplaced">
          <template #header><span style="font-size: 13px">本机柜下未标注 U 位的设备（{{ unplaced.length }}）</span></template>
          <el-tag
            v-for="d in unplaced" :key="d.id"
            class="unplaced-tag"
            :color="CATEGORY_COLOR[d.category] || '#909399'"
            style="color: #fff; border: none"
            @click="openDetail(d)"
          >{{ d.name }}（{{ d.asset_no }}）</el-tag>
        </el-card>
      </div>
    </template>
  </el-card>

  <!-- 设备详情抽屉 -->
  <el-drawer v-model="drawerVisible" title="设备详情" size="380px">
    <template v-if="current">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="资产编号">{{ current.asset_no }}</el-descriptions-item>
        <el-descriptions-item label="设备名称">{{ current.name }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ current.category }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="STATUS_TAG_TYPE[current.status] || 'info'" size="small">{{ current.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="品牌 / 型号">{{ [current.brand, current.model].filter(Boolean).join(' / ') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="SN">{{ current.sn || '-' }}</el-descriptions-item>
        <el-descriptions-item label="位置">{{ current.room_name || '-' }} / {{ current.cabinet_name || '-' }} / {{ current.u_position || '-' }}</el-descriptions-item>
        <el-descriptions-item label="带内 IP">{{ current.ip_inband_v4 || '-' }}<span v-if="current.ip_inband_v6"> / {{ current.ip_inband_v6 }}</span></el-descriptions-item>
        <el-descriptions-item label="带外 IP">{{ current.ip_outband_v4 || '-' }}<span v-if="current.ip_outband_v6"> / {{ current.ip_outband_v6 }}</span></el-descriptions-item>
        <el-descriptions-item label="保修到期">{{ current.warranty_end || '-' }}</el-descriptions-item>
        <el-descriptions-item label="责任人">{{ current.owner || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注">{{ current.remark || '-' }}</el-descriptions-item>
      </el-descriptions>
      <el-button style="margin-top: 16px" type="primary" plain @click="$router.push('/equipment')">
        去设备台账查看
      </el-button>
    </template>
  </el-drawer>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import { CATEGORY, CATEGORY_COLOR, STATUS_TAG_TYPE } from '../constants/dicts'

const U_HEIGHT = 28

const rooms = ref([])
const allCabinets = ref([])
const roomId = ref(null)
const cabinetId = ref(null)
const devices = ref([])
const allRoomDevices = ref([])  // 机房总览用
const loading = ref(false)
const drawerVisible = ref(false)
const current = ref(null)

const cabinetsOfRoom = computed(() =>
  allCabinets.value.filter((c) => c.room_id === roomId.value)
)
const currentRoomName = computed(() =>
  rooms.value.find((r) => r.id === roomId.value)?.name || ''
)
const currentCabinet = computed(() =>
  allCabinets.value.find((c) => c.id === cabinetId.value)
)

// 解析 U 位："U10" → [10,10]；"U10-U12"/"U10-12" → [10,12]；"10" → [10,10]
function parseU(pos) {
  if (!pos) return null
  const m = String(pos).trim().match(/^[Uu]?(\d+)(?:\s*-\s*[Uu]?(\d+))?$/)
  if (!m) return null
  const a = parseInt(m[1])
  const b = m[2] ? parseInt(m[2]) : a
  return [Math.min(a, b), Math.max(a, b)]
}

const placed = computed(() => {
  const out = []
  for (const d of devices.value) {
    const span = parseU(d.u_position)
    if (span) out.push({ device: d, startU: span[0], endU: span[1] })
  }
  return out
})

const unplaced = computed(() =>
  devices.value.filter((d) => !parseU(d.u_position))
)

const usedUCount = computed(() =>
  placed.value.reduce((sum, p) => sum + (p.endU - p.startU + 1), 0)
)

// 机架行：从最高 U 到 U1；设备在其最高 U 处渲染整块
const rackRows = computed(() => {
  const cap = currentCabinet.value?.capacity_u || 42
  const rows = []
  const topAt = {}   // u -> {device, span}
  const covered = new Set()
  for (const p of placed.value) {
    topAt[p.endU] = { device: p.device, span: p.endU - p.startU + 1 }
    for (let u = p.startU; u < p.endU; u++) covered.add(u)
  }
  for (let u = cap; u >= 1; u--) {
    if (topAt[u]) {
      rows.push({ u, device: topAt[u].device, isTop: true, span: topAt[u].span })
    } else if (covered.has(u)) {
      rows.push({ u, device: true, isTop: false })
    } else {
      rows.push({ u, device: null })
    }
  }
  return rows
})

async function loadRefs() {
  const [r, c] = await Promise.all([api.get('/rooms'), api.get('/cabinets')])
  rooms.value = r.data
  allCabinets.value = c.data
  if (rooms.value.length && !roomId.value) roomId.value = rooms.value[0].id
  await loadRoomDevices()
}

async function loadRoomDevices() {
  if (!roomId.value) return
  const { data } = await api.get('/equipment', { params: { room_id: roomId.value, page_size: 100 } })
  allRoomDevices.value = data.items
}

function onRoomChange() {
  cabinetId.value = null
  devices.value = []
  loadRoomDevices()
}

async function loadDevices() {
  if (!cabinetId.value) return
  loading.value = true
  try {
    const { data } = await api.get('/equipment', {
      params: { cabinet_id: cabinetId.value, page_size: 100 }
    })
    devices.value = data.items
  } finally {
    loading.value = false
  }
}

function usedU(cabinet) {
  return allRoomDevices.value
    .filter((d) => d.cabinet_id === cabinet.id)
    .reduce((sum, d) => {
      const span = parseU(d.u_position)
      return sum + (span ? span[1] - span[0] + 1 : 0)
    }, 0)
}

function usageColor(ratio) {
  if (ratio > 0.9) return '#f56c6c'
  if (ratio > 0.7) return '#e6a23c'
  return '#67c23a'
}

function openDetail(d) {
  current.value = d
  drawerVisible.value = true
}

onMounted(loadRefs)
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.legend { display: flex; gap: 12px; }
.legend-item { font-size: 12px; color: #606266; display: flex; align-items: center; gap: 4px; }
.legend-dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }

.cab-card { cursor: pointer; }
.cab-name { font-weight: 600; font-size: 15px; }
.cab-usage { font-size: 12px; color: #909399; margin: 6px 0; }

.rack-layout { max-width: 560px; }
.rack-info { text-align: center; margin-bottom: 10px; }
.rack-title { font-size: 16px; font-weight: 600; }
.rack-sub { font-size: 12px; color: #909399; margin-top: 4px; }

.rack-scroll { max-height: calc(100vh - 300px); overflow-y: auto; }
.rack {
  display: grid;
  grid-template-columns: 44px 1fr;
  border: 2px solid #1d2939;
  border-radius: 8px;
  overflow: hidden;
  background: #1d2939;
}
.u-label {
  height: 28px;
  line-height: 28px;
  text-align: center;
  font-size: 11px;
  color: #98a2b3;
  background: #1d2939;
  border-bottom: 1px solid #344054;
}
.u-slot { height: 26px; margin-bottom: 2px; }
.u-slot.empty { background: #f5f7fa; border: 1px dashed #d0d5dd; box-sizing: border-box; border-radius: 3px; }
.u-slot.covered { margin: 0; height: 2px; }
.u-slot.device {
  border-radius: 3px;
  color: #fff;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  transition: filter 0.15s;
  box-sizing: border-box;
}
.u-slot.device:hover { filter: brightness(1.15); }
.dev-name { font-size: 12px; font-weight: 600; white-space: nowrap; }
.dev-asset { font-size: 10px; opacity: 0.85; white-space: nowrap; }

.unplaced { margin-top: 16px; }
.unplaced-tag { margin: 0 8px 8px 0; cursor: pointer; }
</style>
