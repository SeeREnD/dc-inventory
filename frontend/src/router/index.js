import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue') },
  {
    path: '/',
    component: () => import('../layout/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '统计看板' } },
      { path: 'equipment', component: () => import('../views/EquipmentList.vue'), meta: { title: '设备台账' } },
      { path: 'rooms', component: () => import('../views/RoomManage.vue'), meta: { title: '机房机柜' } },
      { path: 'changes', component: () => import('../views/ChangeLog.vue'), meta: { title: '变更记录' } },
      { path: 'system-log', component: () => import('../views/SystemLog.vue'), meta: { title: '系统日志', adminOnly: true } },
      { path: 'backup', component: () => import('../views/BackupManage.vue'), meta: { title: '备份管理', adminOnly: true } },
      { path: 'users', component: () => import('../views/UserManage.vue'), meta: { title: '用户管理', adminOnly: true } }
    ]
  }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.isLoggedIn) return '/login'
  if (to.path === '/login' && auth.isLoggedIn) return '/'
  if (to.meta.adminOnly && auth.role !== 'admin') return '/'
})

export default router
