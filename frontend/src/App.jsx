import { useState, useEffect, useRef } from 'react'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import Message from './components/Message'
import TypingIndicator from './components/TypingIndicator'
import ChatInput from './components/ChatInput'
import EmptyState from './components/EmptyState'
const STORAGE_KEY = 'space_chat_history'

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [] } catch { return [] }
}

function saveHistory(h) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(h))
}

export default function App() {
  const [history, setHistory] = useState(loadHistory)        // [{id, title, messages}]
  const [activeChatId, setActiveChatId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const bottomRef = useRef(null)

  const activeChat = history.find(c => c.id === activeChatId) || null
  const messages = activeChat?.messages || []

  useEffect(() => { saveHistory(history) }, [history])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const newChat = () => setActiveChatId(null)

  const selectChat = (id) => setActiveChatId(id)

  const deleteChat = (id) => {
    setHistory(prev => prev.filter(c => c.id !== id))
    if (activeChatId === id) setActiveChatId(null)
  }

  const sendMessage = async (query) => {
    const userMsg = { role: 'user', text: query }

    // Create a new chat session if none is active
    let chatId = activeChatId
    if (!chatId) {
      chatId = Date.now().toString()
      const title = query.length > 40 ? query.slice(0, 40) + '…' : query
      setHistory(prev => [{ id: chatId, title, messages: [userMsg] }, ...prev])
      setActiveChatId(chatId)
    } else {
      setHistory(prev => prev.map(c =>
        c.id === chatId ? { ...c, messages: [...c.messages, userMsg] } : c
      ))
    }

    setLoading(true)

    try {
      const res = await fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, n_results: 5 }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)

      const botMsg = { role: 'assistant', text: data.answer, sources: data.sources }
      setHistory(prev => prev.map(c =>
        c.id === chatId ? { ...c, messages: [...c.messages, botMsg] } : c
      ))
    } catch (e) {
      const errMsg = { role: 'assistant', text: `⚠️ ${e.message}`, sources: [] }
      setHistory(prev => prev.map(c =>
        c.id === chatId ? { ...c, messages: [...c.messages, errMsg] } : c
      ))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden">
      <Sidebar
        open={sidebarOpen}
        history={history}
        activeChatId={activeChatId}
        onNew={newChat}
        onSelect={selectChat}
        onDelete={deleteChat}
      />

      <div className="flex flex-col flex-1 min-w-0">
        <Header onToggleSidebar={() => setSidebarOpen(o => !o)} />

        <div className="flex-1 overflow-y-auto chat-scroll px-4 py-6">
          {messages.length === 0
            ? <EmptyState onSuggestion={sendMessage} />
            : (
              <div className="max-w-3xl mx-auto flex flex-col gap-6">
                {messages.map((m, i) => (
                  <Message key={i} role={m.role} text={m.text} sources={m.sources} />
                ))}
                {loading && <TypingIndicator />}
                <div ref={bottomRef} />
              </div>
            )
          }
        </div>

        <ChatInput onSend={sendMessage} loading={loading} />
      </div>
    </div>
  )
}
