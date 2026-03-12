/**
 * Виджет деталей звонка -- композиция подкомпонентов.
 *
 * Каждый блок вынесен в отдельный файл:
 * - TranscriptPanel: live-транскрипт
 * - SessionInfo: параметры сессии + CRM
 * - AIRequestsPanel: запросы и ответы ИИ
 * - PipelineTimingsPanel: тайминги пайплайна
 */
import { formatTime, formatTimestamp } from "@/shared/lib";
import type { CallSession } from "@/shared/types";

import { TranscriptPanel } from "./TranscriptPanel";
import { SessionInfo } from "./SessionInfo";
import { AIRequestsPanel } from "./AIRequestsPanel";
import { PipelineTimingsPanel } from "./PipelineTimingsPanel";

interface CallDetailProps {
  call: CallSession;
}

export function CallDetail({ call }: CallDetailProps) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">
            {call.caller_name || call.caller_number}
          </h2>
          <p className="text-sm text-muted-foreground">{call.caller_number}</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-mono font-bold text-primary">
            {formatTime(call.duration_seconds)}
          </div>
          <p className="text-xs text-muted-foreground">
            Начало: {formatTimestamp(call.started_at)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <TranscriptPanel call={call} />
        <SessionInfo call={call} />
        <AIRequestsPanel call={call} />
        <PipelineTimingsPanel call={call} />
      </div>
    </div>
  );
}
