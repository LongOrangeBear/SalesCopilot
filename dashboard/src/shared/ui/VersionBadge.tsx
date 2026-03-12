/**
 * VersionBadge -- отображает текущую версию приложения.
 *
 * Загружает version.json (генерируется deploy.sh при деплое)
 * и показывает версию + короткий хеш коммита в футере.
 */
import { useState, useEffect } from "react";

interface VersionInfo {
  version: string;
  commit: string;
  buildNumber: number;
  deployedAt: string;
}

export function VersionBadge() {
  const [info, setInfo] = useState<VersionInfo | null>(null);

  useEffect(() => {
    fetch("/version.json?" + Date.now())
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => data && setInfo(data))
      .catch(() => {});
  }, []);

  if (!info) {
    return (
      <span className="text-[10px] text-muted-foreground/50">
        dev
      </span>
    );
  }

  return (
    <span
      className="text-[10px] text-muted-foreground/50 cursor-default"
      title={`Commit: ${info.commit}\nDeployed: ${info.deployedAt}`}
    >
      v{info.version}
    </span>
  );
}
