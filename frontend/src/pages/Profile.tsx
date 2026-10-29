import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { ArrowLeft, User, Lock, Loader2, CheckCircle2 } from 'lucide-react'

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user)
  const changePassword = useAuthStore((s) => s.changePassword)
  const navigate = useNavigate()

  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (!oldPassword || !newPassword || !confirmPassword) {
      setError('请填写所有字段')
      return
    }
    if (newPassword.length < 6) {
      setError('新密码至少6个字符')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('两次新密码输入不一致')
      return
    }

    setLoading(true)
    try {
      await changePassword(oldPassword, newPassword)
      setSuccess('密码修改成功')
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      setError(err.response?.data?.detail || '密码修改失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="max-w-md mx-auto">
        {/* Header */}
        <button
          onClick={() => navigate('/chat')}
          className="flex items-center gap-1.5 text-gray-500 hover:text-gray-700 mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">返回聊天</span>
        </button>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden animate-fade-in">
          {/* User Info */}
          <div className="px-8 pt-8 pb-6 border-b border-gray-100">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center">
                <User className="w-7 h-7 text-blue-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{user?.username}</h3>
                <span className="inline-block mt-0.5 px-2 py-0.5 text-xs font-medium rounded-full bg-blue-50 text-blue-700">
                  {user?.role === 'admin' ? '管理员' : '普通用户'}
                </span>
              </div>
            </div>
          </div>

          {/* Change Password */}
          <div className="px-8 py-6">
            <div className="flex items-center gap-2 mb-5">
              <Lock className="w-4 h-4 text-gray-500" />
              <h4 className="text-sm font-semibold text-gray-900">修改密码</h4>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
              </div>
            )}
            {success && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                {success}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1.5">旧密码</label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1.5">新密码</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                  placeholder="至少6个字符"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1.5">确认新密码</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                  placeholder="再次输入新密码"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium rounded-xl transition-colors shadow-sm"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                {loading ? '保存中...' : '保存修改'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
