<template>
  <el-card shadow="never">
    <!-- 搜索筛选栏 -->
    <div class="toolbar">
      <el-input
        v-model="query.keyword"
        placeholder="搜索资产编号/名称/SN/型号/IP/责任人"
        clearable
        style="width: 260px"
        @keyup.enter="onSearch"
        @clear="onSearch"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="query.status" placeholder="状态" clearable style="width: 110px" @change="onSearch">
        <el-option v-for="s in STATUS" :key="s" :label="s" :value="s" />
      </el-select>
      <el-select v-model="query.category" placeholder="类型" clearable style="width: 120px" @change="onSearch">
        <el-option v-for="c in CATEGORY" :key="c" :label="c" :value="c" />
      </el-select>
      <el-select v-model="query.room_id" placeholder="机房" clearable style="width: 130px" @change="onRoomChange">
        <el-option v-for="r in rooms" :key="r.id" :label="r.name" :value="r.id" />
      </el-select>
      <el-select v-model="query.cabinet_id" placeholder="机柜" clearable style="width: 120px" :disabled="!query.room_id" @change="onSearch">
        <el-option v-for="c in filterCabinets" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <el-button type="primary" @click="onSearch">查询</el-button>
      <el-button @click="onReset">重置</el-button>
      <div style="flex: 1" />
      <template v-if="auth.canEdit">
        <el-button @click="importVisible = true">导入</el-button>
        <el-button
          type="danger"
          plain
          :disabled="!selection.length"
          @click="onBatchDelete"
        >
          批量删除<template v-if="selection.length">（{{ selection.length }}）</template>
        </el-button>
      </template>
      <el-tooltip content="导出当前筛选结果（不筛选则导出全部，上限10000行）" placement="bottom">
        <el-button @click="exportExcel">导出</el-button>
      </el-tooltip>
      <el-button v-if="auth.canEdit" type="primary" @click="openForm()">新增设备</el-button>
    </div>

    <!-- 列表 -->
    <el-table
      :data="items"
      v-loading="loading"
      stripe
      border
      @selection-change="onSelectionChange"
      @sort-change="onSortChange"
      :default-sort="{ prop: 'created_at', order: 'descending' }"
    >
      <el-table-column v-if="auth.canEdit" type="selection" width="44" />
      <el-table-column prop="asset_no" label="资产编号" width="130" sortable="custom" />
      <el-table-column prop="name" label="设备名称" min-width="120" sortable="custom" show-overflow-tooltip />
      <el-table-column prop="category" label="类型" width="90" />
      <el-table-column prop="brand" label="品牌" width="90" show-overflow-tooltip />
      <el-table-column prop="model" label="型号" min-width="110" show-overflow-tooltip />
      <el-table-column prop="sn" label="SN序列号" width="120" show-overflow-tooltip />
      <el-table-column label="机房 / 机柜" width="140">
        <template #default="{ row }">
          {{ row.room_name || '-' }}<template v-if="row.cabinet_name"> / {{ row.cabinet_name }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="u_position" label="U位" width="60" align="center" />
      <el-table-column prop="ip" label="IP" width="120" show-overflow-tooltip />
      <el-table-column label="状态" width="82" align="center">
        <template #default="{ row }">
          <el-tag :type="STATUS_TAG_TYPE[row.status] || 'info'" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="保修到期" width="118" prop="warranty_end" sortable="custom">
        <template #default="{ row }">
          <span :class="warrantyClass(row.warranty_end)">
            {{ row.warranty_end || '-' }}
            <el-tooltip v-if="warrantyState(row.warranty_end) === 'soon'" content="30天内过保">
              <el-icon style="vertical-align: -2px"><WarningFilled /></el-icon>
            </el-tooltip>
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="owner" label="责任人" width="90" show-overflow-tooltip />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button v-if="auth.canEdit" link type="primary" @click="openForm(row)">编辑</el-button>
          <el-button link type="primary" @click="viewLogs(row)">记录</el-button>
          <el-popconfirm v-if="auth.canEdit" title="确认删除该设备？" @confirm="del(row)">
            <template #reference>
              <el-button link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
          <span v-if="!auth.canEdit" style="color:#c0c4cc;font-size:12px">只读</span>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无设备，点击右上角「新增设备」或「导入」开始" :image-size="80" />
      </template>
    </el-table>

    <el-pagination
      v-model:current-page="query.page"
      v-model:page-size="query.page_size"
      :total="total"
      :page-sizes="[20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      style="margin-top: 12px; justify-content: flex-end"
      @size-change="load"
      @current-change="load"
    />
  </el-card>

  <!-- 新增/编辑对话框（带校验） -->
  <el-dialog v-model="formVisible" :title="form.id ? '编辑设备' : '新增设备'" width="680px" :close-on-click-modal="false">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="92px">
      <el-row :gutter="16">
        <el-col :span="12"><el-form-item label="资产编号" prop="asset_no"><el-input v-model.trim="form.asset_no" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="设备名称" prop="name"><el-input v-model.trim="form.name" /></el-form-item></el-col>
        <el-col :span="12">
          <el-form-item label="类型" prop="category">
            <el-select v-model="form.category" style="width: 100%">
              <el-option v-for="c in CATEGORY" :key="c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="状态" prop="status">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="s in STATUS" :key="s" :label="s" :value="s" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12"><el-form-item label="品牌"><el-input v-model.trim="form.brand" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="型号"><el-input v-model.trim="form.model" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="SN序列号"><el-input v-model.trim="form.sn" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="IP" prop="ip"><el-input v-model.trim="form.ip" placeholder="192.168.1.10" /></el-form-item></el-col>
        <el-col :span="12">
          <el-form-item label="机房">
            <el-select v-model="form.room_id" clearable style="width: 100%" @change="form.cabinet_id = null">
              <el-option v-for="r in rooms" :key="r.id" :label="r.name" :value="r.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="机柜">
            <el-select v-model="form.cabinet_id" clearable style="width: 100%" :disabled="!form.room_id">
              <el-option v-for="c in cabinetsOfRoom" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12"><el-form-item label="U位"><el-input v-model.trim="form.u_position" placeholder="U10" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="责任人"><el-input v-model.trim="form.owner" /></el-form-item></el-col>
        <el-col :span="12">
          <el-form-item label="采购日期" prop="purchase_date">
            <el-date-picker v-model="form.purchase_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="保修到期" prop="warranty_end">
            <el-date-picker v-model="form.warranty_end" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="24"><el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item></el-col>
      </el-row>
    </el-form>
    <template #footer>
      <el-button @click="formVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>

  <!-- 导入对话框 -->
  <el-dialog v-model="importVisible" title="Excel 导入" width="480px">
    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      按资产编号去重：已存在则更新，不存在则新增。机房不存在会自动创建。
      <el-link type="primary" style="margin-left: 8px" @click="downloadTemplate">下载模板</el-link>
    </el-alert>
    <input ref="fileInput" type="file" accept=".xlsx" style="display: none" @change="onFileChange" />
    <el-button type="primary" style="width: 100%" @click="$refs.fileInput.click()">选择 .xlsx 文件</el-button>
    <div v-if="report" style="margin-top: 12px">
      <el-alert type="success" :closable="false">
        新增 {{ report.created }} 条，更新 {{ report.updated }} 条，失败 {{ report.failed }} 条
      </el-alert>
      <el-alert v-if="report.errors.length" type="error" :closable="false" style="margin-top: 8px">
        <div v-for="(e, i) in report.errors.slice(0, 10)" :key="i">{{ e }}</div>
      </el-alert>
    </div>
  </el-dialog>

  <!-- 变更记录对话框 -->
  <el-dialog v-model="logVisible" title="设备变更记录" width="720px">
    <el-table :data="logs" v-loading="logLoading" stripe border max-height="480">
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="action" label="操作" width="80" />
      <el-table-column prop="operator" label="操作人" width="100" />
      <el-table-column label="详情" min-width="300">
        <template #default="{ row }"><span class="log-detail">{{ formatDetail(row) }}</span></template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, WarningFilled } from '@element-plus/icons-vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { STATUS, CATEGORY, STATUS_TAG_TYPE, warrantyState, fmtTime } from '../constants/dicts'

const auth = useAuthStore()
const route = useRoute()

const items = ref([])
const total = ref(0)
const loading = ref(false)
const rooms = ref([])
const allCabinets = ref([])
const selection = ref([])

const query = reactive({
  page: 1, page_size: 20,
  keyword: '', status: '', category: '',
  room_id: null, cabinet_id: null,
  sort_by: 'created_at', order: 'desc'
})

const formVisible = ref(false)
const saving = ref(false)
const formRef = ref(null)
const emptyForm = () => ({
  id: null, asset_no: '', name: '', category: '服务器', status: '在用',
  brand: '', model: '', sn: '', ip: '', room_id: null, cabinet_id: null,
  u_position: '', owner: '', purchase_date: null, warranty_end: null, remark: ''
})
const form = reactive(emptyForm())

const importVisible = ref(false)
const report = ref(null)
const logVisible = ref(false)
const logLoading = ref(false)
const logs = ref([])

const ipPattern = /^((25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)$/
const rules = {
  asset_no: [{ required: true, message: '请填写资产编号', trigger: 'blur' }],
  name: [{ required: true, message: '请填写设备名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择类型', trigger: 'change' }],
  ip: [
    { pattern: ipPattern, message: 'IP 格式不正确', trigger: 'blur' }
  ],
  warranty_end: [
    {
      validator: (rule, value, callback) => {
        if (value && form.purchase_date && new Date(value) < new Date(form.purchase_date)) {
          callback(new Error('保修到期不能早于采购日期'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

const filterCabinets = computed(() =>
  allCabinets.value.filter((c) => c.room_id === query.room_id)
)
const cabinetsOfRoom = computed(() =>
  allCabinets.value.filter((c) => c.room_id === form.room_id)
)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/equipment', { params: { ...query } })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadRefs() {
  const [r, c] = await Promise.all([api.get('/rooms'), api.get('/cabinets')])
  rooms.value = r.data
  allCabinets.value = c.data
}

function onSearch() {
  query.page = 1
  load()
}

function onRoomChange() {
  query.cabinet_id = null
  onSearch()
}

function onReset() {
  Object.assign(query, {
    page: 1, keyword: '', status: '', category: '',
    room_id: null, cabinet_id: null, sort_by: 'created_at', order: 'desc'
  })
  load()
}

function onSortChange({ prop, order: ord }) {
  query.sort_by = ord ? prop : 'created_at'
  query.order = ord === 'ascending' ? 'asc' : 'desc'
  load()
}

function onSelectionChange(rows) {
  selection.value = rows
}

function warrantyClass(w) {
  const s = warrantyState(w)
  if (s === 'soon') return 'warranty-soon'
  if (s === 'expired') return 'warranty-expired'
  return ''
}

function openForm(row) {
  Object.assign(form, emptyForm())
  if (row) Object.assign(form, JSON.parse(JSON.stringify(row)))
  formVisible.value = true
}

async function save() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const { id, ...payload } = form
      if (id) await api.put(`/equipment/${id}`, payload)
      else await api.post('/equipment', payload)
      ElMessage.success('保存成功')
      formVisible.value = false
      load()
    } finally {
      saving.value = false
    }
  })
}

async function del(row) {
  await api.delete(`/equipment/${row.id}`)
  ElMessage.success('删除成功')
  load()
}

async function onBatchDelete() {
  if (!selection.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selection.value.length} 台设备？该操作不可撤销。`,
      '批量删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  const { data } = await api.post('/equipment/batch-delete', {
    ids: selection.value.map((r) => r.id)
  })
  ElMessage.success(`已删除 ${data.deleted} 台设备`)
  selection.value = []
  load()
}

async function viewLogs(row) {
  logVisible.value = true
  logLoading.value = true
  try {
    const { data } = await api.get('/changes', { params: { equipment_id: row.id, page_size: 100 } })
    logs.value = data.items
  } finally {
    logLoading.value = false
  }
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

async function download(url, filename, params = {}) {
  const res = await api.get(url, { responseType: 'blob', params })
  const blobUrl = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  a.click()
  URL.revokeObjectURL(blobUrl)
}

// 导出当前筛选结果（与列表查询条件一致，不含分页/排序）
function exportExcel() {
  const { keyword, status, category, room_id, cabinet_id } = query
  download('/excel/export', '设备台账.xlsx',
    { keyword, status, category, room_id, cabinet_id })
}
function downloadTemplate() { download('/excel/template', '导入模板.xlsx') }

async function onFileChange(ev) {
  const file = ev.target.files[0]
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await api.post('/excel/import', fd)
  report.value = data
  ev.target.value = ''
  load()
}

onMounted(() => {
  // 支持从看板带筛选参数跳转：?status=在用 / ?room_id=1 / ?category=服务器
  if (route.query.status) query.status = String(route.query.status)
  if (route.query.room_id) query.room_id = Number(route.query.room_id)
  if (route.query.category) query.category = String(route.query.category)
  load()
  loadRefs()
})
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.log-detail { font-size: 12px; color: #667085; word-break: break-all; }
.warranty-soon { color: #e6a23c; font-weight: 600; }
.warranty-expired { color: #909399; text-decoration: line-through; }
</style>
