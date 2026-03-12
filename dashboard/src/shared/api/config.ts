/**
 * Конфигурация API -- URL-адресов бэкенда.
 *
 * На продакшене nginx (порт 3211) проксирует /api/ и /ws/ на backend (8211),
 * поэтому используем относительные пути по умолчанию.
 * Для локальной разработки задать VITE_WS_URL и VITE_API_URL в .env.
 */

const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";

export const WS_URL =
  import.meta.env.VITE_WS_URL ||
  `${wsProtocol}//${window.location.host}/ws/dashboard`;

export const API_URL =
  import.meta.env.VITE_API_URL ||
  window.location.origin;
