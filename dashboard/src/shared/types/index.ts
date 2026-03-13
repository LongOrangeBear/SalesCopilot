/**
 * Типы данных -- соответствуют backend/app/models/call_session.py
 */

// --- Сущности звонка ---

export interface Utterance {
  speaker: "client" | "manager";
  text: string;
  timestamp: number;
  is_final: boolean;
  confidence: number;
}

export interface AIRequest {
  request_id: string;
  prompt: string;
  context: string;
  model: string;
  sent_at: number;
  response: string;
  received_at: number;
  duration_ms: number;
}

export interface PipelineTimings {
  audio_transfer_ms: number;
  stt_ms: number;
  llm_ms: number;
  delivery_ms: number;
  total_ms: number;
}

export interface CRMContext {
  contact_name: string;
  company: string;
  deal_stage: string;
  deal_budget: string;
  phone: string;
}

export interface CallSession {
  call_id: string;
  direction: "inbound" | "outbound";
  status: "ringing" | "active" | "on_hold" | "ended";
  caller_number: string;
  caller_name: string;
  callee_number: string;
  callee_name: string;
  manager_extension: string;
  started_at: number;
  answered_at: number | null;
  ended_at: number | null;
  duration_seconds: number;
  current_speaker: "client" | "manager" | null;
  transcript: Utterance[];
  crm_context: CRMContext;
  ai_requests: AIRequest[];
  ai_hints: string[];
  pipeline_timings: PipelineTimings[];
}

// --- Сервисные типы ---

export interface ServiceStatus {
  available: boolean;
  message: string;
  error?: string;
  api_key_suffix?: string;
  folder_id?: string;
}

export interface HealthResponse {
  status: string;
  services: {
    stt: ServiceStatus;
    llm: ServiceStatus;
    asterisk: ServiceStatus;
    crm: ServiceStatus;
  };
  active_calls: number;
  dashboard_connections: number;
}

export interface CheckKeysResponse {
  yandex_stt: ServiceStatus;
  openai: ServiceStatus;
}

// --- Pipeline Log ---

export interface PipelineLogEntry {
  timestamp: number;
  source: string;
  message: string;
  details?: string | null;
  level: "info" | "warning" | "error";
}

// --- WebSocket ---

export interface WSInitData {
  active_calls: CallSession[];
  archived_calls: CallSession[];
}

export type WSCallDetailData = CallSession;

export type WSMessage =
  | { event: "init"; data: WSInitData; timestamp: number }
  | { event: "calls_update"; data: WSInitData; timestamp: number }
  | { event: "call_detail"; data: WSCallDetailData; timestamp: number }
  | { event: "pipeline_log"; data: PipelineLogEntry; timestamp: number }
  | { event: "pipeline_logs_init"; data: { logs: PipelineLogEntry[] }; timestamp: number };
