/**
 * Хук live-таймера звонка.
 *
 * Для активных звонков тикает каждую секунду.
 * Для завершённых -- возвращает финальное значение.
 */
import { useState, useEffect } from "react";
import { formatTime } from "./format";

export function useCallTimer(
  startedAt: number | null,
  isActive: boolean,
  staticDuration?: number,
): string {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isActive || !startedAt) {
      setElapsed(0);
      return;
    }

    // Начальное значение
    setElapsed(Math.floor(Date.now() / 1000 - startedAt));

    const interval = setInterval(() => {
      setElapsed(Math.floor(Date.now() / 1000 - startedAt));
    }, 1000);

    return () => clearInterval(interval);
  }, [startedAt, isActive]);

  // Для завершённых звонков используем staticDuration
  if (!isActive && staticDuration !== undefined) {
    return formatTime(staticDuration);
  }

  return formatTime(elapsed);
}
