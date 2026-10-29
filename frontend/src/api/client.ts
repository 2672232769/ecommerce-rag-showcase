import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：自动附加 JWT 令牌
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：401 统一处理（通过事件通知而非全页刷新）
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 清除本地凭据
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // 通过自定义事件通知 React 组件，由 ProtectedRoute 用 <Navigate> 无刷新跳转
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    }
    return Promise.reject(error)
  }
)

export default apiClient
