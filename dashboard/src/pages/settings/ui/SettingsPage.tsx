/**
 * Страница настроек -- read-only обзор текущей конфигурации.
 */
import { useState, useEffect, useCallback } from "react";
import {
  Phone,
  Mic,
  Brain,
  Server,
  RefreshCw,
  Copy,
  Check,
  AlertCircle,
  BookOpen,
} from "lucide-react";
import { cn } from "@/shared/lib";
import { API_URL } from "@/shared/api";
import type { SettingsResponse } from "@/shared/types/settings";

// --- Status dot ---

function StatusDot({ available }: { available: boolean }) {
  return (
    <span
      className={cn(
        "inline-block w-2 h-2 rounded-full flex-shrink-0",
        available
          ? "bg-green-400 shadow-[0_0_6px_rgba(34,197,94,0.5)]"
          : "bg-red-400 shadow-[0_0_6px_rgba(239,68,68,0.5)]"
      )}
    />
  );
}

// --- Copy button ---

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className="p-1 rounded hover:bg-secondary/50 text-muted-foreground hover:text-foreground transition-colors"
      title="Скопировать"
    >
      {copied ? (
        <Check className="w-3.5 h-3.5 text-green-400" />
      ) : (
        <Copy className="w-3.5 h-3.5" />
      )}
    </button>
  );
}

// --- Settings card ---

function SettingsCard({
  icon,
  title,
  status,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  status?: { available: boolean; message?: string };
  children: React.ReactNode;
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-primary/10 text-primary">{icon}</div>
          <h3 className="font-semibold text-sm">{title}</h3>
        </div>
        {status && (
          <div className="flex items-center gap-2 text-xs">
            <StatusDot available={status.available} />
            <span
              className={cn(
                status.available ? "text-green-400" : "text-red-400"
              )}
            >
              {status.available ? "Подключено" : "Недоступно"}
            </span>
          </div>
        )}
      </div>
      {status && !status.available && status.message && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-destructive/10 text-destructive text-xs">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          {status.message}
        </div>
      )}
      <div className="space-y-1">{children}</div>
    </div>
  );
}

// --- Key-value row ---

function Row({
  label,
  value,
  copyable = false,
  mono = false,
}: {
  label: string;
  value: string | number | boolean | null;
  copyable?: boolean;
  mono?: boolean;
}) {
  const displayValue =
    value === null ? "--" : typeof value === "boolean" ? (value ? "Да" : "Нет") : String(value);

  return (
    <div className="flex items-center justify-between py-1.5 text-xs border-b border-border/50 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <div className="flex items-center gap-1.5">
        <span className={cn("text-foreground", mono && "font-mono text-[11px]")}>
          {displayValue}
        </span>
        {copyable && value !== null && <CopyButton text={String(value)} />}
      </div>
    </div>
  );
}

// --- Main page ---

export function SettingsPage() {
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_URL}/api/settings`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json: SettingsResponse = await resp.json();
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  if (loading && !data) {
    return (
      <div className="flex flex-1 items-center justify-center text-muted-foreground text-sm">
        Загрузка настроек...
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3">
        <AlertCircle className="w-8 h-8 text-destructive" />
        <p className="text-sm text-destructive">{error}</p>
        <button
          onClick={fetchSettings}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-primary/10 text-primary text-xs hover:bg-primary/20 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Повторить
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="flex flex-1 overflow-hidden">
      <main className="flex-1 overflow-y-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold">Настройки</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Текущая конфигурация системы (read-only)
            </p>
          </div>
          <button
            onClick={fetchSettings}
            disabled={loading}
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
              "bg-secondary/50 text-muted-foreground hover:text-foreground hover:bg-secondary",
              loading && "opacity-50 cursor-not-allowed"
            )}
          >
            <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
            Обновить
          </button>
        </div>

        {/* Cards grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Asterisk */}
          <SettingsCard
            icon={<Phone className="w-4 h-4" />}
            title="Asterisk / Телефония"
            status={{ available: true, message: "" }}
          >
            <Row label="Сервер" value={data.asterisk.host} copyable mono />
            <Row label="SIP порт" value={data.asterisk.sip_port} copyable />
            <Row label="ARI порт" value={data.asterisk.ari_port} />

            <div className="mt-3 mb-1">
              <span className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">
                SIP-аккаунты
              </span>
            </div>
            <div className="rounded-lg border border-border/50 overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-secondary/30">
                    <th className="text-left px-3 py-1.5 text-muted-foreground font-medium">Имя</th>
                    <th className="text-left px-3 py-1.5 text-muted-foreground font-medium">Ext</th>
                    <th className="text-left px-3 py-1.5 text-muted-foreground font-medium">Username</th>
                  </tr>
                </thead>
                <tbody>
                  {data.asterisk.accounts.map((acc) => (
                    <tr key={acc.extension} className="border-t border-border/30">
                      <td className="px-3 py-1.5">{acc.name}</td>
                      <td className="px-3 py-1.5 font-mono">{acc.extension}</td>
                      <td className="px-3 py-1.5 font-mono text-muted-foreground">
                        {acc.username}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SettingsCard>

          {/* Yandex SpeechKit */}
          <SettingsCard
            icon={<Mic className="w-4 h-4" />}
            title="Yandex SpeechKit"
            status={data.yandex_speechkit.status}
          >
            <Row label="Folder ID" value={data.yandex_speechkit.folder_id} copyable mono />
            <Row label="API Key" value={data.yandex_speechkit.api_key} mono />
          </SettingsCard>

          {/* OpenAI */}
          <SettingsCard
            icon={<Brain className="w-4 h-4" />}
            title="OpenAI"
            status={data.openai.status}
          >
            <Row label="API Key" value={data.openai.api_key} mono />
          </SettingsCard>

          {/* Server */}
          <SettingsCard
            icon={<Server className="w-4 h-4" />}
            title="Сервер"
          >
            <Row label="Host" value={data.server.host} />
            <Row label="Port" value={data.server.port} />
            <Row label="Debug" value={data.server.debug} />
            <Row label="Dashboard URL" value={data.server.dashboard_url} copyable mono />
          </SettingsCard>

          {/* Quick reference */}
          <SettingsCard
            icon={<BookOpen className="w-4 h-4" />}
            title="Шпаргалка"
          >
            <div className="space-y-2 text-xs text-muted-foreground">
              <div>
                <span className="text-foreground font-medium">Dialplan: </span>
                <span className="font-mono">{data.asterisk.dialplan.pattern}</span>
              </div>
              <div>
                <span className="text-foreground font-medium">Эхо-тест: </span>
                <span className="font-mono">{data.asterisk.dialplan.echo_test}</span>
                <span> (набрать для проверки аудио)</span>
              </div>

              <div className="pt-2 border-t border-border/50">
                <p className="text-[11px] leading-relaxed">
                  {data.asterisk.dialplan.note}
                </p>
              </div>

              <div className="pt-2 border-t border-border/50 space-y-1">
                <p className="text-foreground font-medium text-[11px] uppercase tracking-wider mb-1.5">
                  Быстрые номера
                </p>
                {data.asterisk.accounts.map((acc) => (
                  <div key={acc.extension} className="flex items-center justify-between">
                    <span>Позвонить {acc.name}</span>
                    <span className="font-mono text-foreground">{acc.extension}</span>
                  </div>
                ))}
                <div className="flex items-center justify-between">
                  <span>Эхо-тест</span>
                  <span className="font-mono text-foreground">{data.asterisk.dialplan.echo_test}</span>
                </div>
              </div>
            </div>
          </SettingsCard>
        </div>
      </main>
    </div>
  );
}
