/**
 * Панель таймингов пайплайна.
 */
import { BarChart3 } from "lucide-react";
import { cn } from "@/shared/lib";
import type { CallSession } from "@/shared/types";

interface PipelineTimingsPanelProps {
  call: CallSession;
}

export function PipelineTimingsPanel({ call }: PipelineTimingsPanelProps) {
  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-2 border-b border-border bg-secondary/30 flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-orange-400" />
        <span className="font-medium text-sm">Тайминги пайплайна</span>
      </div>
      <div className="p-4 space-y-3">
        {call.pipeline_timings.map((t, i) => (
          <div key={i} className="space-y-2">
            {[
              { label: "Передача аудио", value: t.audio_transfer_ms, color: "bg-blue-500" },
              { label: "STT (Yandex)", value: t.stt_ms, color: "bg-yellow-500" },
              { label: "LLM (OpenAI)", value: t.llm_ms, color: "bg-purple-500" },
              { label: "Доставка", value: t.delivery_ms, color: "bg-green-500" },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-muted-foreground">{label}</span>
                  <span className="font-mono">{value}мс</span>
                </div>
                <div className="h-2 bg-secondary rounded-full overflow-hidden">
                  <div
                    className={cn("h-full rounded-full transition-all", color)}
                    style={{
                      width: `${Math.min((value / t.total_ms) * 100, 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
            <div className="flex justify-between text-sm font-medium pt-1 border-t border-border">
              <span>Итого</span>
              <span className="text-primary font-mono">{t.total_ms}мс</span>
            </div>
          </div>
        ))}
        {call.pipeline_timings.length === 0 && (
          <p className="text-muted-foreground text-sm text-center py-4">
            Нет данных о таймингах
          </p>
        )}
      </div>
    </div>
  );
}
