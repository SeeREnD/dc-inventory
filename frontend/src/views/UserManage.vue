<template>
  <el-card shadow="never">
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">新增用户</el-button>
    </div>

    <el-table :data="users" v-loading="loading" stripe border>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" width="160" />
      <el-table-column label="角色" width="140">
        <template #default="{ row }">
          <el-select v-model="row.role" size="small" @change="update(row, 'role', row.role)">
            <el-option label="管理员" value="admin" />
            <el-option label="编辑" value="editor" />
            <el-option label="只读" value="viewer" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="220">
        <template #default="{ row }">
          <el-button link type="primary" @click="resetPwd(row)">重置密码</el-button>
          <el-button v-if="row.is_active" link type="warning" @click="update(row, 'is_active', false)">禁用</el-button>
          <el-button v-else link type="success" @click="update(row, 'is_active', true)">启用</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="createVisible" title="新增用户" width="420px">
    <el-form label-width="80px">
      <el-form-item label="用户名" required><el-input v-model="createForm.username" /></el-form-item>
      <el-form-item label="密码" required><el-input v-model="createForm.password" type="password" show-password /></el-form-item>
      <el-form-item label="角色">
        <el-select v-model="createForm.role" style="width: 100%">
          <el-option label="管理员" value="admin" />
          <el-option label="编辑" value="editor" />
          <el-option label="只读" value="viewer" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createVisible = false">取消</el-button>
      <el-button type="primary" @click="create">创建</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="pwdVisible" :title="`重置密码：${pwdUser?.username || ''}`" width="400px">
    <el-input v-model="newPwd" type="password" show-password placeholder="输入新密码" />
    <template #footer>
      <el-button @click="pwdVisible = false">取消</el-button>
      <el-button type="primary" @click="doResetPwd">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const users = ref([])
const loading = ref(false)
const createVisible = ref(false)
const createForm = reactive({ username: '', password: '', role: 'viewer' })
const pwdVisible = ref(false)
const pwdUser = ref(null)
const newPwd = ref('')

async function load() {
  loading.value = true
  try {
    users.value = (await api.get('/users')).data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(createForm, { username: '', password: '', role: 'viewer' })
  createVisible.value = true
}

async function create() {
  if (!createForm.username || !createForm.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  await api.post('/users', createForm)
  ElMessage.success('创建成功')
  createVisible.value = false
  load()
}

async function update(row, key, value) {
  try {
    await api.put(`/users/${row.id}`, { [key]: value })
    ElMessage.success('已更新')
  } catch {
    load()
  }
}

function resetPwd(row) {
  pwdUser.value = row
  newPwd.value = ''
  pwdVisible.value = true
}

async function doResetPwd() {
  if (!newPwd.value) {
    ElMessage.warning('请输入新密码')
    return
  }
  await api.put(`/users/${pwdUser.value.id}`, { password: newPwd.value })
  ElMessage.success('密码已重置')
  pwdVisible.value = false
}

function fmtTime(t) {
  return t ? new Date(t).toLocaleString('zh-CN') : ''
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  margin-bottom: 12px;
}
</style>
