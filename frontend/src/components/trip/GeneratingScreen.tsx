export function GeneratingScreen() {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-center space-y-3">
      <div className="flex justify-center">
        <div className="w-10 h-10 rounded-full border-2 border-amber-400 border-t-transparent animate-spin" />
      </div>
      <div>
        <h2 className="text-base font-semibold text-amber-800">
          AI is generating itinerary options…
        </h2>
        <p className="text-sm text-amber-700/70 mt-1">
          This usually takes 20–60 seconds. This page will update automatically.
        </p>
      </div>
    </div>
  );
}
