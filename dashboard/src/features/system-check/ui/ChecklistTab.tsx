/**
 * Фича: чеклист системы -- проверка здоровья сервисов и API-ключей.
 */
import { useState, useEffect, useCallback } from "react";
import { cn } from "@/shared/lib";
import { useApi } from "@/shared/api";
import { CheckItem } from "@/shared/ui";
import type { HealthResponse, CheckKeysResponse } from "@/shared/types";

export function ChecklistTab() {
  const { fetchApi } = useApi();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [keys, setKeys] = useState<CheckKeysResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [h, k] = await Promise.all([
        fetchApi<HealthResponse>("/api/health"),
        fetchApi<CheckKeysResponse>("/api/check-keys"),
      ]);
      setHealth(h);
      setKeys(k);
    } catch (e) {
      console.error("Checklist fetch error:", e);
    } finally {
      setLoading(false);
    }
  }, [fetchApi]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  }, [refresh]);

  if (loading && !health) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Чеклист системы</h2>
        <button
          onClick={refresh}
          disabled={loading}
          className={cn(
            "px-3 py-1.5 text-xs font-medium rounded-lg border transition-all",
            "bg-secondary hover:bg-secondary/80 border-border",
            loading && "opacity-50"
          )}
        >
          {loading ? "Проверка..." : "Обновить"}
        </button>
      </div>

      {/* API Keys */}
      <div>
        <h3 className="text-sm font-semibold text-muted-foreground uppercase mb-3">
          API ключи
        </h3>
        <div className="space-y-2">
          {keys && (
            <>
              <CheckItem
                label="Yandex SpeechKit (STT)"
                available={keys.yandex_stt.available}
                message={keys.yandex_stt.message}
                details={`Key: ${keys.yandex_stt.api_key_suffix || "---"} | Folder: ${keys.yandex_stt.folder_id || "---"}`}
              />
              <CheckItem
                label="OpenAI (LLM)"
                available={keys.openai.available}
                message={keys.openai.message}
                details={`Key: ${keys.openai.api_key_suffix || "---"}`}
              />
            </>
          )}
        </div>
      </div>

      {/* Services */}
      <div>
        <h3 className="text-sm font-semibold text-muted-foreground uppercase mb-3">
          Сервисы
        </h3>
        <div className="space-y-2">
          {health && (
            <>
              <CheckItem
                label="Yandex SpeechKit (STT)"
                available={health.services.stt.available}
                message={health.services.stt.message}
              />
              <CheckItem
                label="OpenAI (LLM)"
                available={health.services.llm.available}
                message={health.services.llm.message}
              />
              <CheckItem
                label="Asterisk (Телефония)"
                available={health.services.asterisk.available}
                message={health.services.asterisk.message}
              />
              <CheckItem
                label="Bitrix24 (CRM)"
                available={health.services.crm.available}
                message={health.services.crm.message}
              />
            </>
          )}
        </div>
      </div>

      {/* System */}
      {health && (
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground uppercase mb-3">
            Система
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-card border border-border rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-primary">{health.active_calls}</div>
              <div className="text-xs text-muted-foreground">Активных звонков</div>
            </div>
            <div className="bg-card border border-border rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-primary">{health.dashboard_connections}</div>
              <div className="text-xs text-muted-foreground">Подключений WS</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
