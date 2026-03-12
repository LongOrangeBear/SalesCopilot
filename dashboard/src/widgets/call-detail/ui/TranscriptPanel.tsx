/**
 * Панель live-транскрипта.
 */
import { MessageSquare } from "lucide-react";
import { cn, formatTimestamp } from "@/shared/lib";
import { SpeakingIndicator } from "@/shared/ui";
import type { CallSession } from "@/shared/types";

interface TranscriptPanelProps {
  call: CallSession;
}

export function TranscriptPanel({ call }: TranscriptPanelProps) {
  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-2 border-b border-border bg-secondary/30 flex items-center gap-2">
        <MessageSquare className="w-4 h-4 text-primary" />
        <span className="font-medium text-sm">Live-транскрипт</span>
        {call.current_speaker && (
          <span className="ml-auto text-xs text-green-400 flex items-center gap-1">
            <SpeakingIndicator active />
            {call.current_speaker === "client" ? "Клиент" : "Менеджер"}
          </span>
        )}
      </div>
      <div className="p-4 max-h-[300px] overflow-y-auto space-y-2">
        {call.transcript.map((u, i) => (
          <div
            key={i}
            className={cn(
              "text-sm p-2 rounded-lg",
              u.speaker === "client"
                ? "bg-blue-500/10 border-l-2 border-blue-500"
                : "bg-green-500/10 border-l-2 border-green-500"
            )}
          >
            <div className="flex items-center justify-between mb-1">
              <span
                className={cn(
                  "text-xs font-semibold",
                  u.speaker === "client" ? "text-blue-400" : "text-green-400"
                )}
              >
                {u.speaker === "client" ? "Клиент" : "Менеджер"}
              </span>
              <span className="text-xs text-muted-foreground">
                {formatTimestamp(u.timestamp)}
              </span>
            </div>
            <p className="text-foreground/90">{u.text}</p>
          </div>
        ))}
        {call.transcript.length === 0 && (
          <p className="text-muted-foreground text-sm text-center py-4">
            Ожидание транскрипции...
          </p>
        )}
      </div>
    </div>
  );
}
