import { CheckCircle, XCircle } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AICallLog } from "@/types";

interface AILogsSectionProps {
  logs: AICallLog[];
}

export function AILogsSection({ logs }: AILogsSectionProps) {
  if (logs.length === 0) {
    return (
      <p className="text-sm text-cream/40 py-4 text-center">
        No AI generation calls recorded yet.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow className="border-border hover:bg-transparent">
            <TableHead className="text-cream/50">When</TableHead>
            <TableHead className="text-cream/50">Model</TableHead>
            <TableHead className="text-cream/50">Provider</TableHead>
            <TableHead className="text-cream/50 text-right">
              Latency (ms)
            </TableHead>
            <TableHead className="text-cream/50 text-right">Tokens in</TableHead>
            <TableHead className="text-cream/50 text-right">
              Tokens out
            </TableHead>
            <TableHead className="text-cream/50 text-center">Valid</TableHead>
            <TableHead className="text-cream/50">Error</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {logs.map((log) => (
            <TableRow key={log.id} className="border-border hover:bg-muted/20">
              <TableCell className="text-cream/60 text-xs whitespace-nowrap">
                {new Date(log.created_at).toLocaleString()}
              </TableCell>
              <TableCell className="text-cream text-xs font-mono">
                {log.model_used}
              </TableCell>
              <TableCell className="text-cream/60 text-xs capitalize">
                {log.provider}
              </TableCell>
              <TableCell className="text-right text-cream/60 text-xs">
                {log.latency_ms !== null ? log.latency_ms.toLocaleString() : "—"}
              </TableCell>
              <TableCell className="text-right text-cream/60 text-xs">
                {log.token_count_input !== null
                  ? log.token_count_input.toLocaleString()
                  : "—"}
              </TableCell>
              <TableCell className="text-right text-cream/60 text-xs">
                {log.token_count_output !== null
                  ? log.token_count_output.toLocaleString()
                  : "—"}
              </TableCell>
              <TableCell className="text-center">
                {log.response_valid ? (
                  <CheckCircle className="w-4 h-4 text-green-400 mx-auto" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-400 mx-auto" />
                )}
              </TableCell>
              <TableCell className="text-red-400 text-xs max-w-[200px] truncate">
                {log.error_message ?? ""}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
