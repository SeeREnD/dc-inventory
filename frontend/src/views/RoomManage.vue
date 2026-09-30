<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-button v-if="auth.canEdit" type="primary" @click="openRoom()">新增机房</el-button>
    </div>

    <el-table :data="rooms" v-loading="loading" stripe border>
      <el-table-column prop="name" label="机房名称" width="180" />
      <el-table-column prop="location" label="位置" min-width="150" />
      <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button link type="primary" @click="openRoom(row)" :disabled="!auth.canEdit">编辑</el-button>
          <el-popconfirm v-if="auth.canEdit" title="确认删除该机房？" @confirm="delRoom(row)">
            <template #reference><el-button link type="danger">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-divider content-position="left">机柜</el-divider>

    <div class="toolbar">
      <el-select v-model="filterRoom" placeholder="按机房筛选" clearable style="width: 160px" @change="loadCabinets">
        <el-option v-for="r in rooms" :key="r.id" :label="r.name" :value="r.id" />
      </el-select>
      <el-button v-if="auth.canEdit" type="primary" @click="openCabinet()">新增机柜</el-button>
    </div>

    <el-table :data="cabinets" v-loading="cLoading" stripe border>
      <el-table-column prop="room_name" label="所属机房" width="160" />
      <el-table-column prop="name" label="机柜名称" width="140" />
      <el-table-column prop="capacity_u" label="容量(U)" width="100" />
      <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button link type="primary" @click="openCabinet(row)" :disabled="!auth.canEdit">编辑</el-button>
          <el-popconfirm v-if="auth.canEdit" title="确认删除该机柜？" @confirm="delCabinet(row)">
            <template #reference><el-button link type="danger">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <!-- 机房对话框 -->
  <el-dialog v-model="roomVisible" :title="roomForm.id ? '编辑机房' : '新增机房'" width="420px">
    <el-form label-width="80px">
      <el-form-item label="名称" required><el-input v-model="roomForm.name" /></el-form-item>
      <el-form-item label="位置"><el-input v-model="roomForm.location" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="roomForm.remark" type="textarea" :rows="2" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="roomVisible = false">取消</el-button>
      <el-button type="primary" @click="saveRoom">保存</el-button>
    </template>
  </el-dialog>

  <!-- 机柜对话框 -->
  <el-dialog v-model="cabVisible" :title="cabForm.id ? '编辑机柜' : '新增机柜'" width="420px">
    <el-form label-width="80px">
      <el-form-item label="机房" required>
        <el-select v-model="cabForm.room_id" style="width: 100%">
          <el-option v-for="r in rooms" :key="r.id" :label="r.name" :value="r.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="名称" required><el-input v-model="cabForm.name" /></el-form-item>
      <el-form-item label="容量(U)"><el-input-number v-model="cabForm.capacity_u" :min="1" :max="100" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="cabForm.remark" type="textarea" :rows="2" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="cabVisible = false">取消</el-button>
      <el-button type="primary" @click="saveCabinet">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const rooms = ref([])
const cabinets = ref([])
const loading = ref(false)
const cLoading = ref(false)
const filterRoom = ref(null)

const roomVisible = ref(false)
const roomForm = reactive({ id: null, name: '', location: '', remark: '' })
const cabVisible = ref(false)
const cabForm = reactive({ id: null, room_id: null, name: '', capacity_u: 42, remark: '' })

async function loadRooms() {
  loading.value = true
  try {
    rooms.value = (await api.get('/rooms')).data
  } finally {
    loading.value = false
  }
}

async function loadCabinets() {
  cLoading.value = true
  try {
    const params = filterRoom.value ? { room_id: filterRoom.value } : {}
    cabinets.value = (await api.get('/cabinets', { params })).data
  } finally {
    cLoading.value = false
  }
}

function openRoom(row) {
  Object.assign(roomForm, { id: null, name: '', location: '', remark: '' })
  if (row) Object.assign(roomForm, JSON.parse(JSON.stringify(row)))
  roomVisible.value = true
}

async function saveRoom() {
  if (!roomForm.name) {
    ElMessage.warning('请填写机房名称')
    return
  }
  const { id, ...payload } = roomForm
  if (id) await api.put(`/rooms/${id}`, payload)
  else await api.post('/rooms', payload)
  ElMessage.success('保存成功')
  roomVisible.value = false
  loadRooms()
}

async function delRoom(row) {
  await api.delete(`/rooms/${row.id}`)
  ElMessage.success('删除成功')
  loadRooms()
  loadCabinets()
}

function openCabinet(row) {
  Object.assign(cabForm, { id: null, room_id: filterRoom.value || rooms.value[0]?.id, name: '', capacity_u: 42, remark: '' })
  if (row) Object.assign(cabForm, JSON.parse(JSON.stringify(row)))
  cabVisible.value = true
}

async function saveCabinet() {
  if (!cabForm.room_id || !cabForm.name) {
    ElMessage.warning('请选择机房并填写名称')
    return
  }
  const { id, ...payload } = cabForm
  if (id) await api.put(`/cabinets/${id}`, payload)
  else await api.post('/cabinets', payload)
  ElMessage.success('保存成功')
  cabVisible.value = false
  loadCabinets()
}

async function delCabinet(row) {
  await api.delete(`/cabinets/${row.id}`)
  ElMessage.success('删除成功')
  loadCabinets()
}

onMounted(() => {
  loadRooms()
  loadCabinets()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
</style>
