import { useState } from "react";
import { CheckCircle, Mail, XCircle } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { admin } from "@/lib/api";
import type { Participant, Trip } from "@/types";

interface ParticipantsSectionProps {
  participants: Participant[];
  trip: Trip;
}

export function ParticipantsSection({ participants, trip }: ParticipantsSectionProps) {
  const { user } = useAuth();
  const [resendingAll, setResendingAll] = useState(false);
  const [resendingId, setResendingId] = useState<number | null>(null);

  const inVotingPhase = trip.status === "VOTING" || trip.status === "ITERATING";

  const statusFlag = (p: Participant) =>
    inVotingPhase ? p.has_voted_current_iteration : p.preferences_submitted;

  const submittedCount = participants.filter(statusFlag).length;

  const counterLabel = inVotingPhase
    ? `${submittedCount.toString()} of ${participants.length.toString()} votes submitted`
    : `${submittedCount.toString()} of ${participants.length.toString()} preferences submitted`;

  const columnHeader = inVotingPhase ? "Voted" : "Preferences";

  const handleResendAll = async () => {
    setResendingAll(true);
    try {
      await admin.resendAll(trip.id);
    } finally {
      setResendingAll(false);
    }
  };

  const handleResendOne = async (participantId: number) => {
    setResendingId(participantId);
    try {
      await admin.resendOne(trip.id, participantId);
    } finally {
      setResendingId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-black/70">{counterLabel}</h3>
        <div className="flex items-center gap-3">
          <span className="text-xs text-black/40">
            {participants.length} participant{participants.length !== 1 ? "s" : ""}
          </span>
          {participants.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => { void handleResendAll(); }}
              disabled={resendingAll}
              className="text-xs h-7"
            >
              <Mail className="w-3 h-3 mr-1" />
              {resendingAll ? "Sending..." : "Resend all"}
            </Button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full bg-brand transition-all"
          style={{
            width:
              participants.length > 0
                ? `${Math.round((submittedCount / participants.length) * 100).toString()}%`
                : "0%",
          }}
        />
      </div>

      {participants.length === 0 ? (
        <p className="text-sm text-black/40 py-4 text-center">
          No participants yet.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="text-black/50">Email</TableHead>
              <TableHead className="text-black/50">Name</TableHead>
              <TableHead className="text-black/50 text-center">
                {columnHeader}
              </TableHead>
              <TableHead className="text-black/50">Joined</TableHead>
              <TableHead className="text-black/50" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {participants.map((p) => {
              const isOrganizer = user != null && p.email === user.email;
              const done = statusFlag(p);
              const isResending = resendingId === p.id;
              return (
                <TableRow key={p.id} className="border-border hover:bg-muted/20">
                  <TableCell className="text-black text-sm">{p.email}</TableCell>
                  <TableCell className="text-black/60 text-sm">
                    {p.name ?? <span className="text-black/30 italic">—</span>}
                    {isOrganizer && (
                      <Badge className="bg-brand/15 text-brand text-[10px] ml-2 hover:bg-brand/15">
                        Organizer
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-center">
                    {done ? (
                      <CheckCircle className="w-4 h-4 text-green-600 mx-auto" />
                    ) : (
                      <XCircle className="w-4 h-4 text-black/20 mx-auto" />
                    )}
                  </TableCell>
                  <TableCell className="text-black/40 text-xs">
                    {new Date(p.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => { void handleResendOne(p.id); }}
                      disabled={isResending || resendingAll}
                      className="text-xs h-7 text-black/40 hover:text-black"
                    >
                      <Mail className="w-3 h-3 mr-1" />
                      {isResending ? "Sending..." : "Resend"}
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
