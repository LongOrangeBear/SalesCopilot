/**
 * Pipeline Log -- окно логов в реальном времени.
 *
 * Показывает события из AudioSocket, STT, AMI с цветовой разметкой.
 */
import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Trash2, ScrollText } from "lucide-react";
import { cn } from "@/shared/lib";
import type { PipelineLogEntry } from "@/shared/types";

interface PipelineLogProps {
  logs: PipelineLogEntry[];
  onClear: () => void;
}

const SOURCE_COLORS: Record<string, string> = {
  AudioSocket: "text-blue-400",
  STT: "text-emerald-400",
  AMI: "text-amber-400",
};

const LEVEL_COLORS: Record<string, string> = {
  info: "text-muted-foreground",
  warning: "text-amber-400",
  error: "text-red-400",
};

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function LogEntry({ entry }: { entry: PipelineLogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const sourceColor = SOURCE_COLORS[entry.source] || "text-purple-400";
  const levelColor = LEVEL_COLORS[entry.level] || "text-muted-foreground";

  return (
    <div
      className={cn(
        "font-mono text-xs leading-5 px-3 py-0.5 hover:bg-white/[0.02] cursor-pointer transition-colors",
        entry.level === "error" && "bg-red-500/[0.04]",
      )}
      onClick={() => entry.details && setExpanded(!expanded)}
    >
      <span className="text-muted-foreground/50">{formatTime(entry.timestamp)}</span>
      {" "}
      <span className={cn("font-semibold", sourceColor)}>
        [{entry.source}]
      </span>
      {" "}
      <span className={levelColor}>{entry.message}</span>
      {entry.details && !expanded && (
        <span className="text-muted-foreground/30 ml-1">...</span>
      )}
      {expanded && entry.details && (
        <div className="text-muted-foreground/60 pl-6 mt-0.5 whitespace-pre-wrap break-all">
          {entry.details}
        </div>
      )}
    </div>
  );
}

export function PipelineLog({ logs, onClear }: PipelineLogProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Авто-скролл вниз при новых логах
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  // Детекция ручного скролла
  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 40;
    setAutoScroll(isAtBottom);
  };

  return (
    <div className="border-t border-border bg-card/30 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/50 bg-card/50">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <ScrollText className="w-3.5 h-3.5" />
          Pipeline Logs
          <span className="text-muted-foreground/50">({logs.length})</span>
          {collapsed ? (
            <ChevronUp className="w-3 h-3" />
          ) : (
            <ChevronDown className="w-3 h-3" />
          )}
        </button>

        {!collapsed && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAutoScroll(!autoScroll)}
              className={cn(
                "px-2 py-0.5 text-[10px] rounded border transition-all",
                autoScroll
                  ? "bg-primary/10 border-primary/30 text-primary"
                  : "bg-secondary/50 border-border text-muted-foreground"
              )}
            >
              Auto-scroll {autoScroll ? "ON" : "OFF"}
            </button>
            <button
              onClick={onClear}
              className="p-1 text-muted-foreground/50 hover:text-red-400 transition-colors"
              title="Очистить логи"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>

      {/* Log content */}
      {!collapsed && (
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="h-48 overflow-y-auto overflow-x-hidden bg-[#0a0a0f]"
        >
          {logs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-xs text-muted-foreground/30">
              Нет данных. Логи появятся при активном звонке.
            </div>
          ) : (
            logs.map((entry, i) => <LogEntry key={i} entry={entry} />)
          )}
        </div>
      )}
    </div>
  );
}
