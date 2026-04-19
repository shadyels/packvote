import type { ParticipantBrief } from "@/types";

interface ParticipantProgressProps {
  participants: ParticipantBrief[];
}

function getInitialsFromString(value: string): string {
  const parts = value.trim().split(/[\s._-]+/).filter(Boolean);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

function getInitials(name: string | null, emailLocal: string, id: number): string {
  if (name) return getInitialsFromString(name);
  const fromEmail = getInitialsFromString(emailLocal);
  if (fromEmail) return fromEmail;
  return `P${id.toString()}`;
}

export function ParticipantProgress({ participants }: ParticipantProgressProps) {
  const submitted = participants.filter((p) => p.preferences_submitted).length;
  const total = participants.length;

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {submitted} of {total} submitted preferences
      </p>
      <div className="flex flex-wrap gap-2">
        {participants.map((p) => (
          <div
            key={p.id}
            title={p.name ?? `Participant ${p.id.toString()}`}
            className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-colors ${
              p.preferences_submitted
                ? "bg-green-100 text-green-700 ring-1 ring-green-400"
                : "bg-muted text-muted-foreground ring-1 ring-border"
            }`}
          >
            {getInitials(p.name, p.email_local, p.id)}
          </div>
        ))}
      </div>
    </div>
  );
}
