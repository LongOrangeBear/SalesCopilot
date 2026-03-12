/**
 * Панель ИИ-запросов и ответов.
 */
import { Brain } from "lucide-react";
import { formatTimestamp } from "@/shared/lib";
import type { CallSession } from "@/shared/types";

interface AIRequestsPanelProps {
  call: CallSession;
}

export function AIRequestsPanel({ call }: AIRequestsPanelProps) {
  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-2 border-b border-border bg-secondary/30 flex items-center gap-2">
        <Brain className="w-4 h-4 text-purple-400" />
        <span className="font-medium text-sm">ИИ запросы и ответы</span>
      </div>
      <div className="p-4 max-h-[300px] overflow-y-auto space-y-3">
        {call.ai_requests.map((req) => (
          <div key={req.request_id} className="space-y-2">
            {/* Request */}
            <div className="bg-purple-500/5 border border-purple-500/20 rounded-lg p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-purple-400">
                  {`ЗАПРОС -> ${req.model}`}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatTimestamp(req.sent_at)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mb-1">Промпт:</p>
              <p className="text-sm">{req.prompt}</p>
              {req.context && (
                <>
                  <p className="text-xs text-muted-foreground mt-1">Контекст:</p>
                  <p className="text-xs text-muted-foreground">{req.context}</p>
                </>
              )}
            </div>
            {/* Response */}
            <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-green-400">
                  ОТВЕТ
                </span>
                <span className="text-xs text-muted-foreground">
                  {req.duration_ms}мс
                </span>
              </div>
              <p className="text-sm">{req.response}</p>
            </div>
          </div>
        ))}
        {call.ai_requests.length === 0 && (
          <p className="text-muted-foreground text-sm text-center py-4">
            Нет запросов к ИИ
          </p>
        )}
      </div>
    </div>
  );
}
