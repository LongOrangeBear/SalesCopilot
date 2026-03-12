/**
 * App -- корневой компонент-оболочка.
 *
 * Содержит только layout (header + content area) и маршрутизацию по табам.
 * Вся бизнес-логика вынесена в pages/, widgets/, features/.
 */
import { useState } from "react";
import {
  Phone,
  Activity,
  Wifi,
  WifiOff,
  Clock,
  ClipboardCheck,
  Zap,
} from "lucide-react";
import { cn } from "@/shared/lib";
import { useWebSocket } from "@/shared/api";
import { MonitorPage } from "@/pages/monitor";
import { ChecklistPage } from "@/pages/checklist";
import "./index.css";

// --- Табы навигации ---

type TabId = "monitor" | "archive" | "checklist";

const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: "monitor", label: "Монитор", icon: <Activity className="w-4 h-4" /> },
  { id: "archive", label: "Архив", icon: <Clock className="w-4 h-4" /> },
  { id: "checklist", label: "Чеклист", icon: <ClipboardCheck className="w-4 h-4" /> },
];

// --- App ---

function App() {
  const { connected, activeCalls, archivedCalls } = useWebSocket();
  const [activeTab, setActiveTab] = useState<TabId>("monitor");
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="h-14 border-b border-border bg-card/50 backdrop-blur-sm flex items-center justify-between px-6 sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <Zap className="w-5 h-5 text-primary" />
          <h1 className="font-semibold text-sm">SalesCopilot Admin</h1>
        </div>

        <div className="flex items-center gap-6">
          {/* Табы в хидере */}
          <nav className="flex items-center gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                  activeTab === tab.id
                    ? "text-primary bg-primary/10"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                )}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-xs">
              {connected ? (
                <>
                  <Wifi className="w-3.5 h-3.5 text-green-400" />
                  <span className="text-green-400">Подключён</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5 text-red-400" />
                  <span className="text-red-400">Отключён</span>
                </>
              )}
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Phone className="w-3.5 h-3.5" />
              <span>{activeCalls.length} акт.</span>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      {activeTab === "checklist" ? (
        <ChecklistPage />
      ) : (
        <MonitorPage
          calls={activeTab === "monitor" ? activeCalls : archivedCalls}
          selectedCallId={selectedCallId}
          onSelectCall={setSelectedCallId}
        />
      )}
    </div>
  );
}

export default App;
