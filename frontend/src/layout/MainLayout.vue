<template>
  <el-container style="height: 100vh">
    <el-aside width="200px" style="background-color: #1d2939">
      <div class="logo">数据中心资产管理系统 DCAM</div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#1d2939"
        text-color="#98a2b3"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon><span>统计看板</span>
        </el-menu-item>
        <el-menu-item index="/equipment">
          <el-icon><Monitor /></el-icon><span>设备台账</span>
        </el-menu-item>
        <el-menu-item index="/rooms">
          <el-icon><OfficeBuilding /></el-icon><span>机房机柜</span>
        </el-menu-item>
        <el-menu-item index="/changes">
          <el-icon><Document /></el-icon><span>变更记录</span>
        </el-menu-item>
        <el-menu-item v-if="auth.role === 'admin'" index="/system-log">
          <el-icon><Memo /></el-icon><span>系统日志</span>
        </el-menu-item>
        <el-menu-item v-if="auth.role === 'admin'" index="/backup">
          <el-icon><FolderChecked /></el-icon><span>备份管理</span>
        </el-menu-item>
        <el-menu-item v-if="auth.role === 'admin'" index="/users">
          <el-icon><User /></el-icon><span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="title">{{ $route.meta.title || '数据中心设备台账' }}</span>
        <el-dropdown @command="onCommand">
          <span class="user-info">
            {{ auth.user?.username }}（{{ roleLabel }}）
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main style="padding: 16px">
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="pwdVisible" title="修改密码" width="400px">
    <el-form label-width="80px">
      <el-form-item label="原密码">
        <el-input v-model="pwdForm.old_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="新密码">
        <el-input v-model="pwdForm.new_password" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="pwdVisible = false">取消</el-button>
      <el-button type="primary" @click="changePassword">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Odometer, Monitor, OfficeBuilding, Document, User, ArrowDown, Memo, FolderChecked } from '@element-plus/icons-vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const roleLabel = computed(
  () => ({ admin: '管理员', editor: '编辑', viewer: '只读' }[auth.role] || auth.role)
)

const pwdVisible = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '' })

async function onCommand(cmd) {
  if (cmd === 'logout') {
    try { await api.post('/auth/logout') } catch { /* 忽略退出记录失败 */ }
    auth.logout()
    router.push('/login')
  } else if (cmd === 'password') {
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdVisible.value = true
  }
}

async function changePassword() {
  if (!pwdForm.old_password || !pwdForm.new_password) {
    ElMessage.warning('请填写完整')
    return
  }
  await api.put('/auth/password', pwdForm)
  ElMessage.success('密码修改成功')
  pwdVisible.value = false
}
</script>

<style scoped>
.logo {
  height: 56px;
  line-height: 56px;
  text-align: center;
  color: #fff;
  font-weight: 600;
  font-size: 15px;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}
.title {
  font-size: 16px;
  font-weight: 600;
}
.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #344054;
}
.el-menu {
  border-right: none;
}
</style>
