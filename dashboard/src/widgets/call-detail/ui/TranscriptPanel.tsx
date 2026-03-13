/**
 * Панель live-транскрипта -- чат-визуализация.
 *
 * - Иконки клиента (слева, синяя) и менеджера (справа, зелёная) с подсветкой
 * - Пузыри сообщений выровнены по стороне говорящего
 * - Partial results отображаются полупрозрачно
 */
import { MessageSquare, User, Headphones } from "lucide-react";
import { cn, formatTimestamp } from "@/shared/lib";
import { SpeakingIndicator } from "@/shared/ui";
import type { CallSession } from "@/shared/types";

interface TranscriptPanelProps {
  call: CallSession;
}

export function TranscriptPanel({ call }: TranscriptPanelProps) {
  const isClientSpeaking = call.current_speaker === "client";
  const isManagerSpeaking = call.current_speaker === "manager";

  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      {/* Header с иконками говорящих */}
      <div className="px-4 py-2 border-b border-border bg-secondary/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-primary" />
          <span className="font-medium text-sm">Live-транскрипт</span>
        </div>

        {/* Иконки говорящих */}
        <div className="flex items-center gap-4">
          {/* Клиент */}
          <div className={cn(
            "flex items-center gap-1.5 px-2 py-1 rounded-md transition-all duration-300",
            isClientSpeaking
              ? "bg-blue-500/15 text-blue-400"
              : "text-muted-foreground"
          )}>
            <User className={cn(
              "w-4 h-4 transition-all duration-300",
              isClientSpeaking && "speaker-glow-client"
            )} />
            <span className="text-xs font-medium">Клиент</span>
            {isClientSpeaking && <SpeakingIndicator active />}
          </div>

          {/* Менеджер */}
          <div className={cn(
            "flex items-center gap-1.5 px-2 py-1 rounded-md transition-all duration-300",
            isManagerSpeaking
              ? "bg-green-500/15 text-green-400"
              : "text-muted-foreground"
          )}>
            {isManagerSpeaking && <SpeakingIndicator active />}
            <span className="text-xs font-medium">Менеджер</span>
            <Headphones className={cn(
              "w-4 h-4 transition-all duration-300",
              isManagerSpeaking && "speaker-glow-manager"
            )} />
          </div>
        </div>
      </div>

      {/* Чат-область */}
      <div className="p-4 max-h-[400px] overflow-y-auto space-y-3">
        {call.transcript.map((u, i) => {
          const isClient = u.speaker === "client";

          return (
            <div
              key={i}
              className={cn(
                "flex",
                isClient ? "justify-start" : "justify-end"
              )}
            >
              <div
                className={cn(
                  "max-w-[80%] rounded-2xl px-4 py-2.5 transition-opacity",
                  isClient
                    ? "bg-blue-500/10 border border-blue-500/20 rounded-bl-sm"
                    : "bg-green-500/10 border border-green-500/20 rounded-br-sm",
                  !u.is_final && "opacity-50"
                )}
              >
                {/* Имя говорящего */}
                <div className={cn(
                  "text-[10px] font-semibold mb-0.5 uppercase tracking-wider",
                  isClient ? "text-blue-400" : "text-green-400"
                )}>
                  {isClient ? "Клиент" : "Менеджер"}
                </div>

                {/* Текст реплики */}
                <p className={cn(
                  "text-sm text-foreground/90 leading-relaxed",
                  !u.is_final && "italic"
                )}>
                  {u.text}
                  {!u.is_final && (
                    <span className="inline-block ml-1 text-muted-foreground">...</span>
                  )}
                </p>

                {/* Timestamp */}
                <div className={cn(
                  "text-[10px] mt-1",
                  isClient ? "text-blue-400/50" : "text-green-400/50"
                )}>
                  {formatTimestamp(u.timestamp)}
                </div>
              </div>
            </div>
          );
        })}

        {call.transcript.length === 0 && (
          <p className="text-muted-foreground text-sm text-center py-8">
            Ожидание транскрипции...
          </p>
        )}
      </div>
    </div>
  );
}
