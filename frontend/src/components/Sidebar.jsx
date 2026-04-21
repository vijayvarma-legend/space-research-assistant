export default function Sidebar({ open, history, activeChatId, onNew, onSelect, onDelete }) {
  if (!open) return null

  return (
    <aside className="w-64 shrink-0 flex flex-col bg-gray-900 border-r border-gray-800 h-full overflow-hidden">
      {/* New Chat */}
      <div className="p-3 shrink-0">
        <button
          onClick={onNew}
          className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          New Chat
        </button>
      </div>

      {/* History */}
      <div className="flex-1 overflow-y-auto chat-scroll px-2 pb-3">
        {history.length === 0 ? (
          <p className="text-xs text-gray-600 text-center mt-6 px-4">No conversations yet</p>
        ) : (
          <ul className="flex flex-col gap-1">
            {history.map(chat => (
              <li key={chat.id} className="group relative">
                <button
                  onClick={() => onSelect(chat.id)}
                  className={`w-full text-left text-sm px-3 py-2.5 rounded-lg pr-8 truncate transition-colors ${
                    activeChatId === chat.id
                      ? 'bg-gray-700 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                  }`}
                >
                  {chat.title}
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(chat.id) }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 transition-all p-1 rounded"
                  aria-label="Delete"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800 shrink-0">
        <p className="text-xs text-gray-600 text-center">Space Research Assistant</p>
      </div>
    </aside>
  )
}
