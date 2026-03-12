/**
 * Панель информации о сессии + CRM-контекст.
 */
import { Settings, User } from "lucide-react";
import { cn } from "@/shared/lib";
import type { CallSession } from "@/shared/types";

interface SessionInfoProps {
  call: CallSession;
}

export function SessionInfo({ call }: SessionInfoProps) {
  return (
    <div className="bg-card border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-2 border-b border-border bg-secondary/30 flex items-center gap-2">
        <Settings className="w-4 h-4 text-primary" />
        <span className="font-medium text-sm">CallSession</span>
      </div>
      <div className="p-4 space-y-2 text-sm">
        <div className="grid grid-cols-2 gap-2">
          <div className="text-muted-foreground">call_id</div>
          <div className="font-mono text-xs">{call.call_id.slice(0, 12)}...</div>
          <div className="text-muted-foreground">direction</div>
          <div>{call.direction}</div>
          <div className="text-muted-foreground">status</div>
          <div className={cn(
            call.status === "active" ? "text-green-400" : "text-muted-foreground"
          )}>{call.status}</div>
          <div className="text-muted-foreground">current_speaker</div>
          <div>{call.current_speaker || "---"}</div>
          <div className="text-muted-foreground">manager_ext</div>
          <div>{call.manager_extension}</div>
        </div>

        {/* CRM Context */}
        {call.crm_context.contact_name && (
          <div className="mt-3 pt-3 border-t border-border">
            <div className="flex items-center gap-2 mb-2">
              <User className="w-3 h-3 text-primary" />
              <span className="text-xs font-semibold text-muted-foreground uppercase">
                CRM
              </span>
            </div>
            <div className="grid grid-cols-2 gap-1">
              <div className="text-muted-foreground">Контакт</div>
              <div>{call.crm_context.contact_name}</div>
              <div className="text-muted-foreground">Компания</div>
              <div>{call.crm_context.company}</div>
              <div className="text-muted-foreground">Стадия</div>
              <div>{call.crm_context.deal_stage}</div>
              <div className="text-muted-foreground">Бюджет</div>
              <div className="text-primary font-medium">{call.crm_context.deal_budget}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
