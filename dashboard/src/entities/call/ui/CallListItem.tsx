/**
 * Элемент списка звонков в сайдбаре.
 *
 * - Пульсирующая иконка для активных звонков
 * - Live-таймер для активных, статический для завершённых
 * - Индикатор "кто говорит"
 */
import {
  Phone,
  PhoneCall,
  PhoneIncoming,
} from "lucide-react";
import { cn, useCallTimer } from "@/shared/lib";
import { SpeakingIndicator } from "@/shared/ui";
import type { CallSession } from "@/shared/types";

interface CallListItemProps {
  call: CallSession;
  selected: boolean;
  onClick: () => void;
}

export function CallListItem({ call, selected, onClick }: CallListItemProps) {
  const isActive = call.status === "active";
  const timerValue = useCallTimer(
    call.answered_at || call.started_at,
    isActive,
    call.duration_seconds,
  );

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left p-3 rounded-lg border transition-all duration-200",
        "hover:bg-secondary/80",
        selected
          ? "bg-secondary border-primary/50 shadow-lg shadow-primary/5"
          : "bg-card border-border"
      )}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          {isActive ? (
            <PhoneCall className="w-4 h-4 text-green-400 animate-pulse-call" />
          ) : call.direction === "inbound" ? (
            <PhoneIncoming className="w-4 h-4 text-green-400" />
          ) : (
            <Phone className="w-4 h-4 text-blue-400" />
          )}
          <span className="font-medium text-sm">
            {call.caller_name || call.caller_number}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isActive && (
            <SpeakingIndicator active={call.current_speaker !== null} />
          )}
          <span
            className={cn(
              "text-xs px-2 py-0.5 rounded-full font-medium",
              isActive
                ? "bg-green-500/20 text-green-400"
                : call.status === "ringing"
                ? "bg-yellow-500/20 text-yellow-400"
                : "bg-muted text-muted-foreground"
            )}
          >
            {isActive ? "Активный" : call.status === "ringing" ? "Вызов" : "Завершён"}
          </span>
        </div>
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {call.callee_name || call.callee_number} (доб. {call.manager_extension})
        </span>
        <span className={cn("font-mono", isActive && "text-green-400")}>
          {timerValue}
        </span>
      </div>
      {call.current_speaker && isActive && (
        <div className="mt-1 text-xs">
          <span className="text-green-400">
            Говорит: {call.current_speaker === "client" ? "Клиент" : "Менеджер"}
          </span>
        </div>
      )}
    </button>
  );
}
