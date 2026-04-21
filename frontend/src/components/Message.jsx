export default function Message({ role, text, sources }) {
  const isUser = role === 'user'

  return (
    <div className={`flex items-start gap-3 msg-enter ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-indigo-700 flex items-center justify-center text-sm shrink-0">
        {isUser ? '👤' : '🤖'}
      </div>

      <div className={`flex flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Bubble */}
        <div className={`rounded-2xl px-4 py-3 max-w-[75%] shadow-lg text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-gray-800 text-gray-100 rounded-bl-sm border border-gray-700'
        }`}>
          {text}
        </div>

        {/* Source chips */}
        {sources && sources.length > 0 && (
          <div className="flex flex-wrap gap-2 max-w-[75%]">
            {sources.map((s, i) => (
              <span
                key={i}
                title={`Relevance: ${s.distance}`}
                className="inline-flex items-center gap-1 text-xs bg-gray-700 hover:bg-gray-600 text-indigo-300 border border-gray-600 rounded-full px-3 py-1 transition-colors cursor-default select-none"
              >
                <span>📄</span>
                <span>{s.source}</span>
                <span className="text-gray-500">p{s.page_num}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
