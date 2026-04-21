const SUGGESTIONS = [
  'What methods are used to detect exoplanets?',
  'How does atmospheric retrieval work?',
  'What causes space debris accumulation in LEO?',
  'Explain transit photometry for exoplanet detection',
]

export default function EmptyState({ onSuggestion }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 px-4 text-center">
      <div className="text-6xl">🌌</div>
      <div>
        <h2 className="text-xl font-semibold text-gray-200 mb-1">Space Research Assistant</h2>
        <p className="text-sm text-gray-500">Ask questions about your indexed research papers</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl w-full">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSuggestion(s)}
            className="text-left text-sm text-gray-300 bg-gray-800/60 hover:bg-gray-700/60 border border-gray-700 rounded-xl px-4 py-3 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
