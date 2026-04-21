import { useRef } from 'react'

export default function ChatInput({ onSend, loading }) {
  const ref = useRef(null)

  const submit = () => {
    const val = ref.current.value.trim()
    if (!val || loading) return
    onSend(val)
    ref.current.value = ''
    ref.current.style.height = 'auto'
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const onInput = () => {
    const el = ref.current
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }

  return (
    <div className="shrink-0 px-4 py-4 border-t border-gray-800 bg-gray-900">
      <div className="max-w-3xl mx-auto flex items-end gap-3">
        <textarea
          ref={ref}
          rows={1}
          onKeyDown={onKeyDown}
          onInput={onInput}
          placeholder="Ask about exoplanets, space debris, satellite networks…"
          disabled={loading}
          className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none transition-all"
        />
        <button
          onClick={submit}
          disabled={loading}
          className="p-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-150 shrink-0"
          aria-label="Send"
        >
          {loading
            ? <svg className="w-5 h-5 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
            : <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
          }
        </button>
      </div>
    </div>
  )
}
