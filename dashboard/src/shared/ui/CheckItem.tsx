/**
 * Элемент чеклиста -- статус-карточка с иконкой.
 * Переиспользуемый UI-компонент для отображения результатов проверки.
 */
import { CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { cn } from "@/shared/lib";

interface CheckItemProps {
  label: string;
  available: boolean;
  message: string;
  details?: string;
  error?: string;
}

export function CheckItem({ label, available, message, details, error }: CheckItemProps) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 p-4 rounded-lg border transition-all",
        available
          ? "bg-green-500/5 border-green-500/20"
          : "bg-red-500/5 border-red-500/20"
      )}
    >
      <div className="mt-0.5">
        {available ? (
          <CheckCircle className="w-5 h-5 text-green-400" />
        ) : (
          <XCircle className="w-5 h-5 text-red-400" />
        )}
      </div>
      <div className="flex-1">
        <div className="font-medium text-sm">{label}</div>
        <div className="text-xs text-muted-foreground mt-0.5">{message}</div>
        {details && (
          <div className="text-xs text-muted-foreground/70 font-mono mt-1">
            {details}
          </div>
        )}
        {!available && error && (
          <div className="flex items-start gap-1.5 mt-2 text-xs text-red-400/80 bg-red-500/5 rounded px-2 py-1.5">
            <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            <span className="font-mono break-all">{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
