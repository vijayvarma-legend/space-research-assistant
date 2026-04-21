export default function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 msg-enter">
      <div className="w-8 h-8 rounded-full bg-indigo-700 flex items-center justify-center text-sm shrink-0">🤖</div>
      <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-bl-sm px-5 py-4 flex items-center gap-1">
        <span className="dot w-2 h-2 rounded-full bg-indigo-400 inline-block" />
        <span className="dot w-2 h-2 rounded-full bg-indigo-400 inline-block" />
        <span className="dot w-2 h-2 rounded-full bg-indigo-400 inline-block" />
      </div>
    </div>
  )
}
