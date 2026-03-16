import { CheckCircle2 } from "lucide-react";
import { ParticipantProgress } from "./ParticipantProgress";
import type { ParticipantBrief } from "@/types";

interface WaitingScreenProps {
  participants: ParticipantBrief[];
}

export function WaitingScreen({ participants }: WaitingScreenProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-6 space-y-4 text-center">
      <div className="flex justify-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
          <CheckCircle2 className="h-6 w-6 text-green-600" />
        </div>
      </div>
      <div>
        <h2 className="text-base font-semibold text-foreground">
          Preferences submitted!
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Waiting for the rest of the group before AI generates itinerary
          options.
        </p>
      </div>
      <div className="flex justify-center">
        <ParticipantProgress participants={participants} />
      </div>
    </div>
  );
}
