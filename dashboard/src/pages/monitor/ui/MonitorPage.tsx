/**
 * Страница мониторинга -- активные звонки.
 */
import { useEffect } from "react";
import { Activity, PhoneOff } from "lucide-react";
import { CallListItem } from "@/entities/call";
import { CallDetail } from "@/widgets/call-detail";
import type { CallSession } from "@/shared/types";

interface MonitorPageProps {
  calls: CallSession[];
  selectedCallId: string | null;
  onSelectCall: (id: string) => void;
}

export function MonitorPage({ calls, selectedCallId, onSelectCall }: MonitorPageProps) {
  const selectedCall = calls.find((c) => c.call_id === selectedCallId);

  // Авто-выбор первого звонка
  useEffect(() => {
    if (!selectedCallId && calls.length > 0) {
      onSelectCall(calls[0].call_id);
    }
  }, [calls, selectedCallId, onSelectCall]);

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Список звонков */}
      <aside className="w-72 border-r border-border bg-card/30 flex flex-col">
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {calls.length === 0 ? (
            <div className="text-center py-8">
              <PhoneOff className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Нет активных звонков</p>
            </div>
          ) : (
            calls.map((call) => (
              <CallListItem
                key={call.call_id}
                call={call}
                selected={call.call_id === selectedCallId}
                onClick={() => onSelectCall(call.call_id)}
              />
            ))
          )}
        </div>
      </aside>

      {/* Детали звонка */}
      <main className="flex-1 overflow-y-auto p-6">
        {selectedCall ? (
          <CallDetail call={selectedCall} />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Activity className="w-12 h-12 text-muted-foreground/20 mx-auto mb-3" />
              <p className="text-muted-foreground">
                Выберите звонок для просмотра деталей
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
