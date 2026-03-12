/**
 * WebSocket-клиент для real-time обновлений дашборда.
 */
import { useEffect, useRef, useState, useCallback } from "react";
import type { CallSession, WSMessage } from "@/shared/types";
import { WS_URL } from "./config";

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

  return { connected, activeCalls, archivedCalls, lastEvent, sendAction };
}
