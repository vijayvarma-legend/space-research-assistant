export default function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 msg-enter">
      <div className="w-8 h-8 rounded-full bg-indigo-700 flex items-center justify-center text-sm shrink-0">🤖</div>
      <div className="chat-bubble-bot flex items-center gap-1 py-4 px-5">
        <span className="dot w-2 h-2 rounded-full bg-indigo-400 inline-block" />
        <span className="dot w-2 h-2 rounded-full bg-indigo-400 inline-block" />
        <span className="dot w-2 h-2 rounded-full bg-indigo-400 inline-block" />
      </div>
    </div>
  )
}
