import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const api = axios.create({ baseURL: '/api', timeout: 30000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      router.push('/login')
      ElMessage.error('登录已失效，请重新登录')
    } else {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') {
        ElMessage.error(detail)
      } else if (detail) {
        ElMessage.error(detail.map((d) => d.msg).join('；'))
      }
    }
    return Promise.reject(err)
  }
)

export default api
