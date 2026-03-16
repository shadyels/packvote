import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";

const TRAVEL_TIPS = [
  "Ranked-choice voting ensures the group's true favorite wins.",
  "The AI weighs everyone's budget so no one gets priced out.",
  "Packing light? A carry-on saves 30+ minutes at every airport.",
  "Booking flights mid-week is often 10–15% cheaper.",
  "Travel insurance costs ~5% of trip price and covers the unexpected.",
  "The AI reads all preferences simultaneously — no averaging.",
  "Itineraries include day-by-day activities and local tips.",
];

export function GeneratingScreen() {
  const [tipIndex, setTipIndex] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      setVisible(false);
      setTimeout(() => {
        setTipIndex((i) => (i + 1) % TRAVEL_TIPS.length);
        setVisible(true);
      }, 300);
    }, 4000);
    return () => { clearInterval(interval); };
  }, []);

  return (
    <div className="rounded-xl border border-amber-200/60 bg-amber-50/50 p-8 text-center space-y-5">
      {/* Pulsing map pin */}
      <div className="flex justify-center">
        <div className="relative">
          <div className="absolute inset-0 rounded-full bg-amber-300/40 animate-ping" />
          <div className="relative flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 border border-amber-200">
            <MapPin className="h-5 w-5 text-amber-700" />
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-base font-semibold text-amber-800">
          AI is crafting your itinerary options…
        </h2>
        <p className="text-sm text-amber-700/60 mt-1">
          Usually 20–60 seconds. This page updates automatically.
        </p>
      </div>

      {/* Rotating tip */}
      <div
        className="mx-auto max-w-xs rounded-lg border border-amber-200/60 bg-white/60 px-4 py-3 transition-opacity duration-300"
        style={{ opacity: visible ? 1 : 0 }}
      >
        <p className="text-xs text-amber-700/80 italic">
          {TRAVEL_TIPS[tipIndex]}
        </p>
      </div>

      {/* Progress bar */}
      <div className="mx-auto h-1 max-w-xs overflow-hidden rounded-full bg-amber-100">
        <div className="h-full rounded-full bg-amber-400 animate-[progress_40s_linear_infinite]" />
      </div>
    </div>
  );
}
