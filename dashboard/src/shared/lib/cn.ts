/**
 * Утилита для объединения CSS-классов.
 * Комбинирует clsx (условные классы) и tailwind-merge (де-дупликация Tailwind-классов).
 */
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
