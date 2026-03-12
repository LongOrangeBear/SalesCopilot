/**
 * Функции форматирования данных.
 */

/** Форматирует секунды в строку "M:SS". */
export function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** Форматирует UNIX timestamp в локальное время "HH:MM:SS". */
export function formatTimestamp(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("ru-RU");
}
