import { useState, useEffect, useRef, useCallback, useMemo, memo } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useAuthStore } from '../store/authStore'
import { useSessionStore } from '../store/sessionStore'
import { useChatStore } from '../store/chatStore'
import type { Source } from '../types'
import {
  Plus, MessageSquare, Trash2, Edit3, Check, X,
  Send, LogOut, User, Shield, ShoppingBag, Loader2,
  ChevronDown, FileText, Bot,
} from 'lucide-react'

export default function ChatPage() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const {
    sessions, currentSessionId, isLoading: sessionLoading,
    loadSessions, createSession, deleteSession,
    updateSessionTitle, setCurrentSession,
  } = useSessionStore()
  const {
    messages, isLoading, streamingContent, currentSources,
    loadMessages, addUserMessage, startStreaming,
    setSources, appendChunk, finishStreaming, clearChat,
  } = useChatStore()

  const [input, setInput] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // 初始化加载会话列表
  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  // 切换会话时加载消息
  useEffect(() => {
    if (currentSessionId) {
      loadMessages(currentSessionId)
    } else {
      clearChat()
    }
  }, [currentSessionId, loadMessages, clearChat])

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  // SSE 发送消息
  const sendMessage = useCallback(
    async (sessionId: number, question: string) => {
      const token = localStorage.getItem('token')
      if (!token) {
        navigate('/login')
        return
      }

      addUserMessage(question)
      startStreaming()

      try {
        const response = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ session_id: sessionId, question }),
        })

        if (!response.ok) {
          const err = await response.json()
          throw new Error(err.detail || '请求失败')
        }

        const reader = response.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        let completed = false

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          const lines = buffer.split('\n\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            let payload
            try { payload = JSON.parse(line.slice(6)) } catch { continue }
              switch (payload.type) {
                case 'sources':
                  setSources(payload.data)
                  break
                case 'chunk':
                  appendChunk(payload.data)
                  break
                case 'done':
                  completed = true
                  finishStreaming(payload.message_id)
                  // 更新 session 列表以反映更新时间
                  loadSessions()
                  break
                case 'error':
                  throw new Error(payload.data || '模型生成失败')
              }
          }
        }
        if (!completed) throw new Error('回答连接中断，请重试')
      } catch (err: any) {
        appendChunk(`\n\n> ⚠️ 请求失败: ${err.message || '未知错误'}`)
        finishStreaming(Date.now())
      }
    },
    [
      navigate, addUserMessage, startStreaming, setSources,
      appendChunk, finishStreaming, loadSessions,
    ]
  )

  // 发送按钮
  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return

    setInput('')
    inputRef.current?.focus()

    let sessionId = currentSessionId

    // 没有选中会话 → 自动创建
    if (!sessionId) {
      try {
        const session = await createSession()
        sessionId = session.id
        setCurrentSession(sessionId)
        // 自动用首条消息的前几个字作为标题
        const autoTitle = trimmed.length > 20 ? trimmed.slice(0, 20) + '...' : trimmed
        await updateSessionTitle(session.id, autoTitle)
        setCurrentSession(session.id)
      } catch {
        return
      }
    }

    // 如果是新会话的第一条消息，自动更新标题
    if (messages.length === 0 && sessionId) {
      const autoTitle = trimmed.length > 20 ? trimmed.slice(0, 20) + '...' : trimmed
      try {
        await updateSessionTitle(sessionId, autoTitle)
      } catch {
        // 静默失败
      }
    }

    await sendMessage(sessionId, trimmed)
    loadSessions()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleNewSession = async () => {
    clearChat()
    setCurrentSession(null)
  }

  const handleSelectSession = (id: number) => {
    if (id === currentSessionId) return
    setCurrentSession(id)
  }

  const handleDeleteSession = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
    if (!confirm('确定要删除这个会话吗？')) return
    await deleteSession(id)
    if (id === currentSessionId) {
      clearChat()
    }
  }

  const handleStartEdit = (e: React.MouseEvent, id: number, title: string) => {
    e.stopPropagation()
    setEditingId(id)
    setEditTitle(title)
  }

  const handleSaveEdit = async (id: number) => {
    if (editTitle.trim()) {
      await updateSessionTitle(id, editTitle.trim())
    }
    setEditingId(null)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  // 当前会话信息
  const currentSession = useMemo(
    () => sessions.find((s) => s.id === currentSessionId),
    [sessions, currentSessionId]
  )

  return (
    <div className="h-screen flex bg-gray-50 overflow-hidden">
      {/* ============ 侧边栏 ============ */}
      <aside
        className={`${
          sidebarOpen ? 'w-72' : 'w-0'
        } flex-shrink-0 bg-white border-r border-gray-200 flex flex-col transition-all duration-300 overflow-hidden`}
      >
        {/* 侧边栏头部 */}
        <div className="p-4 border-b border-gray-100">
          <button
            onClick={handleNewSession}
            className="w-full flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            新建对话
          </button>
        </div>

        {/* 会话列表 */}
        <div className="flex-1 overflow-y-auto">
          {sessionLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-10 px-4">
              <MessageSquare className="w-8 h-8 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-400">暂无对话记录</p>
              <p className="text-xs text-gray-400 mt-1">点击上方按钮开始新对话</p>
            </div>
          ) : (
            <div className="py-2">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  onClick={() => handleSelectSession(session.id)}
                  className={`group mx-2 mb-0.5 px-3 py-2.5 rounded-xl cursor-pointer transition-colors ${
                    session.id === currentSessionId
                      ? 'bg-blue-50 border border-blue-100'
                      : 'hover:bg-gray-50 border border-transparent'
                  }`}
                >
                  {editingId === session.id ? (
                    <div className="flex items-center gap-1">
                      <input
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="flex-1 px-2 py-1 text-sm border border-blue-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleSaveEdit(session.id)
                          if (e.key === 'Escape') setEditingId(null)
                        }}
                      />
                      <button onClick={() => handleSaveEdit(session.id)} className="p-1 hover:bg-green-100 rounded text-green-600">
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => setEditingId(null)} className="p-1 hover:bg-red-100 rounded text-red-500">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-800 truncate flex-1">
                          {session.title}
                        </p>
                        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 ml-1">
                          <button
                            onClick={(e) => handleStartEdit(e, session.id, session.title)}
                            className="p-1 hover:bg-gray-200 rounded"
                          >
                            <Edit3 className="w-3 h-3 text-gray-400" />
                          </button>
                          <button
                            onClick={(e) => handleDeleteSession(e, session.id)}
                            className="p-1 hover:bg-red-100 rounded"
                          >
                            <Trash2 className="w-3 h-3 text-gray-400 hover:text-red-500" />
                          </button>
                        </div>
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {new Date(session.updated_at).toLocaleDateString('zh-CN')}
                      </p>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 侧边栏底部 */}
        <div className="p-3 border-t border-gray-100 space-y-1">
          {user?.role === 'admin' && (
            <button
              onClick={() => navigate('/admin/knowledge')}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-purple-50 transition-colors text-sm text-purple-700"
            >
              <Shield className="w-4 h-4" />
              知识库管理
            </button>
          )}
          <button
            onClick={() => navigate('/profile')}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-gray-50 transition-colors text-sm text-gray-700"
          >
            <User className="w-4 h-4" />
            {user?.username}
          </button>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-red-50 transition-colors text-sm text-red-600"
          >
            <LogOut className="w-4 h-4" />
            退出登录
          </button>
        </div>
      </aside>

      {/* ============ 主聊天区 ============ */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部栏 */}
        <header className="flex-shrink-0 h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ChevronDown
                className={`w-5 h-5 text-gray-500 transition-transform ${
                  sidebarOpen ? '' : '-rotate-90'
                }`}
              />
            </button>
            <div className="flex items-center gap-2">
              <ShoppingBag className="w-5 h-5 text-blue-600" />
              <h1 className="text-lg font-bold text-gray-900 hidden sm:block">
                电商智能问答
              </h1>
            </div>
          </div>
          {currentSession && (
            <p className="text-sm text-gray-500 truncate max-w-xs">
              {currentSession.title}
            </p>
          )}
        </header>

        {/* 消息列表（虚拟滚动占位 — 后续可集成 react-virtuoso） */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          {!currentSessionId ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center animate-fade-in">
                <div className="w-20 h-20 bg-blue-50 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-lg shadow-blue-100">
                  <Bot className="w-10 h-10 text-blue-600" />
                </div>
                <h2 className="text-xl font-bold text-gray-800 mb-2">电商智能问答助手</h2>
                <p className="text-gray-500 mb-6 max-w-md">
                  基于商品知识库的 AI 问答系统。<br />
                  点击左侧"新建对话"开始提问吧！
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {['这个商品有什么特点？', '有什么推荐的手机？', '这两款产品有什么区别？'].map(
                    (q) => (
                      <button
                        key={q}
                        onClick={async () => {
                          setInput(q)
                          // 需要先创建会话
                          try {
                            const session = await createSession()
                            setCurrentSession(session.id)
                            const autoTitle = q.slice(0, 20) + '...'
                            await updateSessionTitle(session.id, autoTitle)
                            await sendMessage(session.id, q)
                            loadSessions()
                          } catch {
                            // ignore
                          }
                        }}
                        className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-full transition-colors"
                      >
                        {q}
                      </button>
                    )
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.length === 0 && !isLoading && (
                <div className="text-center py-20 animate-fade-in">
                  <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <MessageSquare className="w-8 h-8 text-blue-500" />
                  </div>
                  <p className="text-gray-400">开始提问吧，我会根据知识库为您解答</p>
                </div>
              )}

              {/* 已保存的消息 */}
              {messages.map((msg) => (
                <div key={msg.id} className="animate-slide-up">
                  <MessageBubble message={msg} />
                </div>
              ))}

              {/* 流式生成中的消息 */}
              {isLoading && streamingContent !== '' && (
                <div className="animate-fade-in">
                  <div className="flex gap-3">
                    <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="bg-white rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm border border-gray-100">
                        <div className="markdown-body text-sm text-gray-800">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {streamingContent}
                          </ReactMarkdown>
                        </div>
                      </div>
                      {currentSources && currentSources.length > 0 && (
                        <SourceCards sources={currentSources} />
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* 加载指示器（初始检索时） */}
              {isLoading && streamingContent === '' && (
                <div className="flex gap-3 animate-fade-in">
                  <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-white rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm border border-gray-100">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse-dot" />
                      <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse-dot" style={{ animationDelay: '0.2s' }} />
                      <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse-dot" style={{ animationDelay: '0.4s' }} />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 输入区域 */}
        <div className="flex-shrink-0 bg-white border-t border-gray-200 px-4 py-3">
          <div className="max-w-3xl mx-auto flex items-end gap-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={currentSessionId ? '输入您的问题... (Enter 发送，Shift+Enter 换行)' : '输入问题开始新对话...'}
              rows={1}
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition text-sm max-h-32"
              style={{ minHeight: '44px' }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement
                target.style.height = 'auto'
                target.style.height = Math.min(target.scrollHeight, 128) + 'px'
              }}
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="flex-shrink-0 w-11 h-11 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl flex items-center justify-center transition-colors shadow-sm"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ==================== 消息气泡组件（React.memo 性能优化） ====================

function MessageBubbleComponent({ message }: { message: { id: number; role: string; content: string; sources: Source[] | null } }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* 头像 */}
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          isUser ? 'bg-gray-700' : 'bg-blue-600'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* 内容 */}
      <div className={`flex-1 min-w-0 ${isUser ? 'flex flex-col items-end' : ''}`}>
        <div
          className={`inline-block max-w-[85%] rounded-2xl px-5 py-3.5 shadow-sm ${
            isUser
              ? 'bg-blue-600 text-white rounded-tr-sm'
              : 'bg-white text-gray-800 rounded-tl-sm border border-gray-100'
          }`}
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
          ) : (
            <div className="markdown-body text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* 引用来源（仅 AI 消息） */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourceCards sources={message.sources} />
        )}
      </div>
    </div>
  )
}

const MessageBubble = memo(MessageBubbleComponent)

// ==================== 引用来源卡片 ====================

function SourceCards({ sources }: { sources: Source[] }) {
  return (
    <div className="mt-2 space-y-1.5 max-w-[85%]">
      <p className="text-xs text-gray-400 font-medium flex items-center gap-1">
        <FileText className="w-3 h-3" />
        引用来源
      </p>
      {sources.map((s, i) => (
        <div
          key={i}
          className="bg-amber-50 border border-amber-100 rounded-xl px-3 py-2 text-xs animate-fade-in"
        >
          <p className="text-amber-700 font-medium mb-0.5">📄 {s.source}</p>
          <p className="text-gray-600 leading-relaxed line-clamp-3">{s.content}</p>
        </div>
      ))}
    </div>
  )
}
