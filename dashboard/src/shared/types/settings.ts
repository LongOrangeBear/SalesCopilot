/**
 * Типы ответа GET /api/settings.
 */

export interface SipAccount {
  name: string;
  extension: number;
  username: string;
}

export interface DialplanInfo {
  pattern: string;
  echo_test: number;
  note: string;
}

export interface ServiceStatus {
  available: boolean;
  message?: string;
}

export interface AsteriskSettings {
  host: string;
  sip_port: number;
  ari_port: number;
  accounts: SipAccount[];
  dialplan: DialplanInfo;
}

export interface YandexSettings {
  folder_id: string;
  api_key: string;
  status: ServiceStatus;
}

export interface OpenAISettings {
  api_key: string;
  status: ServiceStatus;
}

export interface ServerSettings {
  host: string;
  port: number;
  debug: boolean;
  dashboard_url: string | null;
}

export interface SettingsResponse {
  asterisk: AsteriskSettings;
  yandex_speechkit: YandexSettings;
  openai: OpenAISettings;
  server: ServerSettings;
}
