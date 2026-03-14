import { CheckCircle, XCircle } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Participant } from "@/types";

interface ParticipantsSectionProps {
  participants: Participant[];
}

export function ParticipantsSection({ participants }: ParticipantsSectionProps) {
  const submitted = participants.filter((p) => p.preferences_submitted).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-cream/70">
          {submitted} of {participants.length} preferences submitted
        </h3>
        <span className="text-xs text-cream/40">
          {participants.length} participant{participants.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-accent transition-all"
          style={{
            width:
              participants.length > 0
                ? `${Math.round((submitted / participants.length) * 100)}%`
                : "0%",
          }}
        />
      </div>

      {participants.length === 0 ? (
        <p className="text-sm text-cream/40 py-4 text-center">
          No participants yet.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="text-cream/50">Email</TableHead>
              <TableHead className="text-cream/50">Name</TableHead>
              <TableHead className="text-cream/50 text-center">
                Preferences
              </TableHead>
              <TableHead className="text-cream/50">Joined</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {participants.map((p) => (
              <TableRow key={p.id} className="border-border hover:bg-muted/20">
                <TableCell className="text-cream text-sm">{p.email}</TableCell>
                <TableCell className="text-cream/60 text-sm">
                  {p.name ?? <span className="text-cream/30 italic">—</span>}
                </TableCell>
                <TableCell className="text-center">
                  {p.preferences_submitted ? (
                    <CheckCircle className="w-4 h-4 text-green-400 mx-auto" />
                  ) : (
                    <XCircle className="w-4 h-4 text-cream/20 mx-auto" />
                  )}
                </TableCell>
                <TableCell className="text-cream/40 text-xs">
                  {new Date(p.created_at).toLocaleDateString()}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
