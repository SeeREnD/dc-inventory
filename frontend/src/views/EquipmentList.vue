<template>
  <el-card shadow="never">
    <!-- 搜索筛选栏 -->
    <div class="toolbar">
      <el-input
        v-model="query.keyword"
        placeholder="搜索资产编号/名称/SN/型号/带内外IP/责任人"
        clearable
        style="width: 280px"
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
      <el-table-column label="带内IP" width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <div>{{ row.ip_inband_v4 || '-' }}</div>
          <div v-if="row.ip_inband_v6" class="ip-sub">{{ row.ip_inband_v6 }}</div>
        </template>
      </el-table-column>
      <el-table-column label="带外IP" width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <div>{{ row.ip_outband_v4 || '-' }}</div>
          <div v-if="row.ip_outband_v6" class="ip-sub">{{ row.ip_outband_v6 }}</div>
        </template>
      </el-table-column>
      <el-table-column label="规格摘要" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="spec-summary">{{ row.spec_summary || '-' }}</span>
        </template>
      </el-table-column>
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
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">详情</el-button>
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

  <!-- 新增/编辑对话框：标签页分区，避免字段堆叠 -->
  <el-dialog v-model="formVisible" :title="form.id ? '编辑设备' : '新增设备'" width="880px" :close-on-click-modal="false">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="92px">
      <el-tabs v-model="activeTab">
        <!-- 基础信息 -->
        <el-tab-pane label="基础信息" name="basic">
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
        </el-tab-pane>

        <!-- 网络地址 -->
        <el-tab-pane label="网络地址" name="network">
          <el-alert type="info" :closable="false" style="margin-bottom: 12px">
            带外 = 管理网（BMC/iDRAC/iLO），带内 = 业务网。IPv6 可留空。
          </el-alert>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="带内IPv4" prop="ip_inband_v4">
                <el-input v-model.trim="form.ip_inband_v4" placeholder="192.168.1.10" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="带内IPv6" prop="ip_inband_v6">
                <el-input v-model.trim="form.ip_inband_v6" placeholder="2001:db8::1" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="带外IPv4" prop="ip_outband_v4">
                <el-input v-model.trim="form.ip_outband_v4" placeholder="10.0.0.10" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="带外IPv6" prop="ip_outband_v6">
                <el-input v-model.trim="form.ip_outband_v6" placeholder="2001:db8::a" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 硬件规格 -->
        <el-tab-pane label="硬件规格" name="specs">
          <el-collapse v-model="specOpen">
            <el-collapse-item title="CPU" name="cpu">
              <el-table :data="form.cpus" size="small" border>
                <el-table-column label="型号" min-width="180">
                  <template #default="{ row }"><el-input v-model.trim="row.model" size="small" placeholder="Intel Xeon Gold 6338" /></template>
                </el-table-column>
                <el-table-column label="颗数" width="100">
                  <template #default="{ row }"><el-input-number v-model="row.sockets" :min="1" size="small" controls-position="right" style="width: 100%" /></template>
                </el-table-column>
                <el-table-column label="每颗核心" width="110">
                  <template #default="{ row }"><el-input-number v-model="row.cores_per_cpu" :min="1" size="small" controls-position="right" style="width: 100%" /></template>
                </el-table-column>
                <el-table-column label="主频GHz" width="110">
                  <template #default="{ row }"><el-input-number v-model="row.freq_ghz" :min="0" :step="0.1" :precision="1" size="small" controls-position="right" style="width: 100%" /></template>
                </el-table-column>
                <el-table-column label="操作" width="60" align="center">
                  <template #default="{ $index }"><el-button link type="danger" @click="form.cpus.splice($index, 1)">删除</el-button></template>
                </el-table-column>
              </el-table>
              <el-button link type="primary" style="margin-top: 6px" @click="form.cpus.push({ model: '', sockets: 2, cores_per_cpu: null, freq_ghz: null })">+ 添加 CPU</el-button>
            </el-collapse-item>

            <el-collapse-item title="显卡（GPU）" name="gpu">
              <el-table :data="form.gpus" size="small" border>
                <el-table-column label="型号" min-width="170">
                  <template #default="{ row }"><el-input v-model.trim="row.model" size="small" placeholder="NVIDIA A100" /></template>
                </el-table-column>
                <el-table-column label="张数" width="100">
                  <template #default="{ row }"><el-input-number v-model="row.count" :min="1" size="small" controls-position="right" style="width: 100%" /></template>
                </el-table-column>
                <el-table-column label="显存GB" width="110">
                  <template #default="{ row }"><el-input-number v-model="row.memory_gb" :min="0" size="small" controls-position="right" style="width: 100%" /></template>
                </el-table-column>
                <el-table-column label="用途" width="120">
                  <template #default="{ row }">
                    <el-select v-model="row.purpose" size="small" placeholder="用途" style="width: 100%">
                      <el-option v-for="p in GPU_PURPOSE" :key="p" :label="p" :value="p" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="60" align="center">
                  <template #default="{ $index }"><el-button link type="danger" @click="form.gpus.splice($index, 1)">删除</el-button></template>
                </el-table-column>
              </el-table>
              <el-button link type="primary" style="margin-top: 6px" @click="form.gpus.push({ model: '', count: 1, memory_gb: null, purpose: '计算' })">+ 添加显卡</el-button>
            </el-collapse-item>

            <el-collapse-item title="硬盘" name="disk">
              <el-table :data="form.disks" size="small" border>
                <el-table-column label="类型" width="120">
                  <template #default="{ row }">
                    <el-select v-model="row.type" size="small" placeholder="类型" style="width: 100%">
                      <el-option v-for="t in DISK_TYPE" :key="t" :label="t" :value="t" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="单块容量GB" width="130">
                  <template #default="{ row }"><el-input-number v-model="row.capacity_gb" :min="0" size="small" controls-position="right" style="width: 100%" /></template>
                </el-table-column>
                <el-table-column label="块数" width="100">
                  <template #default="{ row }"><el-input-number v-model="row.count" :min="1" size="small" controls-position="right" style="width: 100%" /></template>
                </el-table-column>
                <el-table-column label="RAID" width="120">
                  <template #default="{ row }">
                    <el-select v-model="row.raid_level" size="small" placeholder="RAID" style="width: 100%">
                      <el-option v-for="r in RAID_LEVEL" :key="r" :label="r" :value="r" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="角色" width="110">
                  <template #default="{ row }">
                    <el-select v-model="row.role" size="small" placeholder="角色" style="width: 100%">
                      <el-option v-for="r in DISK_ROLE" :key="r" :label="r" :value="r" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="60" align="center">
                  <template #default="{ $index }"><el-button link type="danger" @click="form.disks.splice($index, 1)">删除</el-button></template>
                </el-table-column>
              </el-table>
              <el-button link type="primary" style="margin-top: 6px" @click="form.disks.push({ type: 'NVMe', capacity_gb: null, count: 1, raid_level: '直通', role: '数据' })">+ 添加硬盘</el-button>
            </el-collapse-item>
          </el-collapse>
        </el-tab-pane>
      </el-tabs>
    </el-form>
    <template #footer>
      <el-button @click="formVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>

  <!-- 只读详情抽屉 -->
  <el-drawer v-model="detailVisible" title="设备详情" size="480px">
    <template v-if="detailRow">
      <el-descriptions :column="1" border size="small" title="基础信息">
        <el-descriptions-item label="资产编号">{{ detailRow.asset_no }}</el-descriptions-item>
        <el-descriptions-item label="设备名称">{{ detailRow.name }}</el-descriptions-item>
        <el-descriptions-item label="类型 / 状态">{{ detailRow.category }} / {{ detailRow.status }}</el-descriptions-item>
        <el-descriptions-item label="品牌 / 型号">{{ [detailRow.brand, detailRow.model].filter(Boolean).join(' / ') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="SN">{{ detailRow.sn || '-' }}</el-descriptions-item>
        <el-descriptions-item label="位置">{{ detailRow.room_name || '-' }} / {{ detailRow.cabinet_name || '-' }} / {{ detailRow.u_position || '-' }}</el-descriptions-item>
        <el-descriptions-item label="采购 / 保修">{{ detailRow.purchase_date || '-' }} ~ {{ detailRow.warranty_end || '-' }}</el-descriptions-item>
        <el-descriptions-item label="责任人">{{ detailRow.owner || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注">{{ detailRow.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-descriptions :column="1" border size="small" title="网络地址" style="margin-top: 16px">
        <el-descriptions-item label="带内 IPv4">{{ detailRow.ip_inband_v4 || '-' }}</el-descriptions-item>
        <el-descriptions-item label="带内 IPv6">{{ detailRow.ip_inband_v6 || '-' }}</el-descriptions-item>
        <el-descriptions-item label="带外 IPv4">{{ detailRow.ip_outband_v4 || '-' }}</el-descriptions-item>
        <el-descriptions-item label="带外 IPv6">{{ detailRow.ip_outband_v6 || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="detail-title">硬件规格</div>
      <div v-if="!detailRow.spec_summary" class="detail-empty">-</div>
      <template v-else>
        <el-table v-if="detailRow.cpus?.length" :data="detailRow.cpus" size="small" border style="margin-bottom: 10px">
          <el-table-column label="CPU 型号" prop="model" min-width="150" show-overflow-tooltip />
          <el-table-column label="颗数" prop="sockets" width="60" align="center" />
          <el-table-column label="核心" prop="cores_per_cpu" width="60" align="center" />
          <el-table-column label="GHz" prop="freq_ghz" width="60" align="center" />
        </el-table>
        <el-table v-if="detailRow.gpus?.length" :data="detailRow.gpus" size="small" border style="margin-bottom: 10px">
          <el-table-column label="GPU 型号" prop="model" min-width="150" show-overflow-tooltip />
          <el-table-column label="张数" prop="count" width="60" align="center" />
          <el-table-column label="显存" prop="memory_gb" width="60" align="center" />
          <el-table-column label="用途" prop="purpose" width="70" align="center" />
        </el-table>
        <el-table v-if="detailRow.disks?.length" :data="detailRow.disks" size="small" border>
          <el-table-column label="类型" prop="type" width="90" />
          <el-table-column label="容量GB" prop="capacity_gb" width="90" align="center" />
          <el-table-column label="块数" prop="count" width="60" align="center" />
          <el-table-column label="RAID" prop="raid_level" width="80" />
          <el-table-column label="角色" prop="role" width="70" />
        </el-table>
      </template>
    </template>
  </el-drawer>

  <!-- 导入对话框 -->
  <el-dialog v-model="importVisible" title="Excel 导入" width="480px">
    <el-alert type="info" :closable="false" style="margin-bottom: 12px">
      按资产编号去重：已存在则更新（空单元格保留原值），不存在则新增。机房不存在会自动创建。
      <el-link type="primary" style="margin-left: 8px" @click="downloadTemplate">下载模板</el-link>
    </el-alert>
    <input ref="fileInput" type="file" accept=".xlsx" style="display: none" @change="onFileChange" />
    <el-button type="primary" style="width: 100%" @click="$refs.fileInput.click()">选择 .xlsx 文件</el-button>
    <div v-if="report" style="margin-top: 12px">
      <el-alert type="success" :closable="false">
        新增 {{ report.created }} 条，更新 {{ report.updated }} 条，失败 {{ report.failed }} 条
      </el-alert>
      <el-alert v-if="report.warnings && report.warnings.length" type="warning" :closable="false" style="margin-top: 8px">
        <div v-for="(w, i) in report.warnings.slice(0, 10)" :key="i">{{ w }}</div>
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
import {
  STATUS, CATEGORY, STATUS_TAG_TYPE, warrantyState, fmtTime,
  DISK_TYPE, RAID_LEVEL, GPU_PURPOSE, DISK_ROLE
} from '../constants/dicts'

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
const activeTab = ref('basic')
const specOpen = ref(['cpu'])
const emptyForm = () => ({
  id: null, asset_no: '', name: '', category: '服务器', status: '在用',
  brand: '', model: '', sn: '',
  ip_inband_v4: '', ip_inband_v6: '', ip_outband_v4: '', ip_outband_v6: '',
  cpus: [], gpus: [], disks: [],
  room_id: null, cabinet_id: null,
  u_position: '', owner: '', purchase_date: null, warranty_end: null, remark: ''
})
const form = reactive(emptyForm())

const detailVisible = ref(false)
const detailRow = ref(null)

const importVisible = ref(false)
const report = ref(null)
const logVisible = ref(false)
const logLoading = ref(false)
const logs = ref([])

const ipv4Pattern = /^((25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)$/
const ipv6Pattern = /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|::(ffff(:0{1,4})?:)?((25[0-5]|(2[0-4]|1?[0-9])?[0-9])\.){3}(25[0-5]|(2[0-4]|1?[0-9])?[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1?[0-9])?[0-9])\.){3}(25[0-5]|(2[0-4]|1?[0-9])?[0-9]))$/

const makeIpRule = (pattern, label) => [
  {
    validator: (rule, value, callback) => {
      if (!value) return callback()
      return pattern.test(value) ? callback() : callback(new Error(`${label} 格式不正确`))
    },
    trigger: 'blur'
  }
]

const rules = {
  asset_no: [{ required: true, message: '请填写资产编号', trigger: 'blur' }],
  name: [{ required: true, message: '请填写设备名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择类型', trigger: 'change' }],
  ip_inband_v4: makeIpRule(ipv4Pattern, 'IPv4'),
  ip_outband_v4: makeIpRule(ipv4Pattern, 'IPv4'),
  ip_inband_v6: makeIpRule(ipv6Pattern, 'IPv6'),
  ip_outband_v6: makeIpRule(ipv6Pattern, 'IPv6'),
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
  // 规格字段兜底为数组，避免表格直接渲染 null 报错
  form.cpus = form.cpus || []
  form.gpus = form.gpus || []
  form.disks = form.disks || []
  activeTab.value = 'basic'
  formVisible.value = true
}

function openDetail(row) {
  detailRow.value = row
  detailVisible.value = true
}

async function save() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      // 剔除后端不接收的计算/关联字段
      const {
        id, spec_summary, room_name, cabinet_name, created_at, updated_at, ...payload
      } = form
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
.ip-sub { font-size: 11px; color: #909399; }
.spec-summary { font-size: 12px; color: #606266; }
.detail-title { margin: 16px 0 8px; font-weight: 600; }
.detail-empty { color: #909399; }
</style>
