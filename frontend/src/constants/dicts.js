// 统一字典常量，多页面复用，改一处全局生效
export const STATUS = ['在用', '备用', '维修', '报废', '退役']

export const CATEGORY = ['服务器', '交换机', '存储', '防火墙', '其他']

export const STATUS_TAG_TYPE = {
  在用: 'success',
  备用: 'info',
  维修: 'warning',
  报废: 'danger',
  退役: 'info'
}

export const ROLE_LABEL = {
  admin: '管理员',
  editor: '编辑',
  viewer: '只读'
}

// 保修到期 → 状态：'expired' | 'soon' | 'ok' | null（无保修）
export function warrantyState(warrantyEnd) {
  if (!warrantyEnd) return null
  const end = new Date(warrantyEnd)
  const now = new Date()
  if (end < now) return 'expired'
  const days = (end - now) / (1000 * 60 * 60 * 24)
  if (days <= 30) return 'soon'
  return 'ok'
}

export function fmtDate(t) {
  if (!t) return ''
  const d = new Date(t)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function fmtTime(t) {
  return t ? new Date(t).toLocaleString('zh-CN') : ''
}
