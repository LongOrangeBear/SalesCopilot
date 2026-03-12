/**
 * Страница чеклиста системы.
 */
import { ChecklistTab } from "@/features/system-check";

export function ChecklistPage() {
  return (
    <div className="flex flex-1 overflow-hidden">
      <main className="flex-1 overflow-y-auto p-6">
        <ChecklistTab />
      </main>
    </div>
  );
}
