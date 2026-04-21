export default function Message({ role, text, sources }) {
  const isUser = role === 'user'

  return (
    <div className={`flex items-start gap-3 msg-enter ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 bg-indigo-700">
        {isUser ? '👤' : '🤖'}
      </div>

      <div className={`flex flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Bubble */}
        <div className={isUser ? 'chat-bubble-user' : 'chat-bubble-bot'}>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{text}</p>
        </div>

        {/* Sources */}
        {sources && sources.length > 0 && (
          <div className="flex flex-wrap gap-2 max-w-[75%]">
            {sources.map((s, i) => (
              <span key={i} className="source-chip" title={`Distance: ${s.distance}`}>
                <span>📄</span>
                <span>{s.source}</span>
                <span className="text-gray-500">p{s.page_num}</span>
                <span className="text-gray-600">·</span>
                <span className="text-gray-400">{s.distance}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
