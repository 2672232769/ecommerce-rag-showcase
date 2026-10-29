import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import * as knowledgeApi from '../api/knowledge'
import type { KnowledgeDocument } from '../types'
import {
  ArrowLeft, Upload, FileText, Trash2, Loader2,
  Database, FileIcon, AlertCircle, CheckCircle2, RefreshCw,
} from 'lucide-react'

export default function KnowledgeManagePage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const loadDocuments = useCallback(async () => {
    setLoading(true)
    try {
      const docs = await knowledgeApi.listDocuments()
      setDocuments(docs)
    } catch {
      setError('加载文档列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setError('')
    setSuccess('')
    setUploading(true)

    try {
      await knowledgeApi.uploadDocument(file)
      setSuccess(`文档 "${file.name}" 上传成功`)
      await loadDocuments()
    } catch (err: any) {
      setError(err.response?.data?.detail || '上传失败')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDelete = async (doc: KnowledgeDocument) => {
    if (!confirm(`确定要删除文档 "${doc.filename}" 吗？`)) return
    setError('')
    setSuccess('')
    try {
      await knowledgeApi.deleteDocument(doc.id)
      setSuccess(`文档 "${doc.filename}" 已删除`)
      await loadDocuments()
    } catch {
      setError('删除失败')
    }
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/chat')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-500" />
            </button>
            <div>
              <h1 className="text-xl font-bold text-gray-900">知识库管理</h1>
              <p className="text-sm text-gray-500">管理员专属 - 上传和管理商品知识文档</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadDocuments}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="刷新列表"
            >
              <RefreshCw className={`w-5 h-5 text-gray-500 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.pdf,.csv"
              onChange={handleUpload}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl cursor-pointer transition-colors shadow-sm"
            >
              {uploading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Upload className="w-4 h-4" />
              )}
              {uploading ? '上传中...' : '上传文档'}
            </label>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Messages */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 flex items-center gap-2 animate-fade-in">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700 flex items-center gap-2 animate-fade-in">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            {success}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center">
                <Database className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{documents.length}</p>
                <p className="text-xs text-gray-500">文档总数</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {documents.reduce((sum, d) => sum + d.chunk_count, 0)}
                </p>
                <p className="text-xs text-gray-500">总切片数</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-50 rounded-lg flex items-center justify-center">
                <FileIcon className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {formatSize(documents.reduce((sum, d) => sum + d.file_size, 0))}
                </p>
                <p className="text-xs text-gray-500">总文档大小</p>
              </div>
            </div>
          </div>
        </div>

        {/* Document List */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-gray-200">
            <Upload className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-500 mb-2">知识库为空</h3>
            <p className="text-sm text-gray-400">点击右上角"上传文档"按钮添加知识库内容</p>
            <p className="text-xs text-gray-400 mt-1">支持 .txt .md .pdf .csv 格式</p>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
              <p className="text-sm font-medium text-gray-700">文档列表</p>
            </div>
            <div className="divide-y divide-gray-100">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="px-6 py-4 flex items-center justify-between hover:bg-gray-50/50 transition-colors"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
                      <FileText className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{doc.filename}</p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {doc.file_type.toUpperCase()} · {formatSize(doc.file_size)} · {doc.chunk_count} 个切片 · {new Date(doc.uploaded_at).toLocaleDateString('zh-CN')}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(doc)}
                    className="flex-shrink-0 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors ml-4"
                    title="删除文档"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
