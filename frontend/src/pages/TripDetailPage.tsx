import { useParams } from "react-router-dom";
import { Skeleton } from "@/components/ui/skeleton";

export default function TripDetailPage() {
  const { tripId } = useParams<{ tripId: string }>();
  return (
    <div className="min-h-screen bg-background p-6">
      <Skeleton className="h-8 w-64 mb-4" />
      <p className="text-cream/60 text-sm">Loading trip {tripId}…</p>
    </div>
  );
}
