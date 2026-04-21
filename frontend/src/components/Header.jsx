export default function Header({ onToggleSidebar }) {
  return (
    <header className="flex items-center gap-3 px-4 py-4 border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm shrink-0">
      <button
        onClick={onToggleSidebar}
        className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
        aria-label="Toggle sidebar"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      <div className="flex items-center gap-2">
        <span className="text-xl">🔭</span>
        <h1 className="text-base font-semibold text-white">Space Research Assistant</h1>
      </div>
    </header>
  )
}
