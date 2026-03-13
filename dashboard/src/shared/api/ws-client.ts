/**
 * WebSocket-клиент для real-time обновлений дашборда.
 */
import { useEffect, useRef, useState, useCallback } from "react";
import type { CallSession, WSMessage, PipelineLogEntry } from "@/shared/types";
import { WS_URL } from "./config";

const MAX_LOG_ENTRIES = 500;

function createWebSocket(
  url: string,
  handlers: {
    onOpen: () => void;
    onMessage: (data: string) => void;
    onClose: () => void;
    onError: () => void;
  },
): WebSocket {
  const ws = new WebSocket(url);
  ws.onopen = handlers.onOpen;
  ws.onmessage = (e) => handlers.onMessage(e.data);
  ws.onclose = handlers.onClose;
  ws.onerror = () => {
    handlers.onError();
    ws.close();
  };
  return ws;
}

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [activeCalls, setActiveCalls] = useState<CallSession[]>([]);
  const [archivedCalls, setArchivedCalls] = useState<CallSession[]>([]);
  const [pipelineLogs, setPipelineLogs] = useState<PipelineLogEntry[]>([]);
  const [lastEvent, setLastEvent] = useState<WSMessage | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const handleMessage = useCallback((data: string) => {
    try {
      const msg: WSMessage = JSON.parse(data);
      setLastEvent(msg);

      if (msg.event === "init" || msg.event === "calls_update") {
        setActiveCalls(msg.data.active_calls || []);
        setArchivedCalls(msg.data.archived_calls || []);
      } else if (msg.event === "call_detail") {
        // Обновляем конкретную сессию
        setActiveCalls((prev) =>
          prev.map((c) =>
            c.call_id === msg.data.call_id ? msg.data : c
          )
        );
      } else if (msg.event === "pipeline_log") {
        // Одиночная лог-запись
        setPipelineLogs((prev) => {
          const next = [...prev, msg.data];
          return next.length > MAX_LOG_ENTRIES ? next.slice(-MAX_LOG_ENTRIES) : next;
        });
      } else if (msg.event === "pipeline_logs_init") {
        // Буфер последних логов при подключении
        setPipelineLogs(msg.data.logs || []);
      }
    } catch (e) {
      console.error("[WS] Parse error:", e);
    }
  }, []);

  const sendAction = useCallback((action: string, payload?: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action, ...payload }));
    }
  }, []);

  const clearLogs = useCallback(() => {
    setPipelineLogs([]);
  }, []);

  useEffect(() => {
    let isActive = true;

    function connect() {
      if (!isActive) return;
      if (wsRef.current?.readyState === WebSocket.OPEN) return;

      const ws = createWebSocket(WS_URL, {
        onOpen: () => {
          setConnected(true);
          console.log("[WS] Connected to backend");
        },
        onMessage: handleMessage,
        onClose: () => {
          setConnected(false);
          console.log("[WS] Disconnected. Reconnecting in 3s...");
          if (isActive) {
            reconnectTimer.current = setTimeout(connect, 3000);
          }
        },
        onError: () => {
          console.error("[WS] Error");
        },
      });

      wsRef.current = ws;
    }

    connect();

    return () => {
      isActive = false;
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [handleMessage]);

  return { connected, activeCalls, archivedCalls, pipelineLogs, clearLogs, lastEvent, sendAction };
}
