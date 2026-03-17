import { AlertTriangle, Clock, MapPin } from "lucide-react";
import { format } from "date-fns";

export default function AlertsPanel({ accidents }) {
  const recentAccidents = accidents.filter(acc => acc.status === "new").slice(0, 5);

  return (
    <div className="glass-card p-6" data-testid="alerts-panel">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-6 h-6 text-red-500" />
        <h2 className="text-2xl font-semibold" data-testid="alerts-title">Active Alerts</h2>
      </div>

      {recentAccidents.length === 0 ? (
        <div className="text-center py-8 text-zinc-500" data-testid="no-alerts-message">
          <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No active alerts</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[600px] overflow-y-auto scrollbar-thin pr-2">
          {recentAccidents.map((accident) => (
            <div key={accident.id} className="alert-card" data-testid={`alert-${accident.id}`}>
              <div className="flex items-start justify-between mb-2">
                <span className={`severity-badge severity-${accident.severity}`}>
                  {accident.severity}
                </span>
                <span className="text-xs font-mono text-zinc-500">
                  {format(new Date(accident.timestamp), "HH:mm:ss")}
                </span>
              </div>

              <h3 className="font-semibold text-sm mb-2">{accident.accident_type}</h3>

              <div className="space-y-1 text-xs text-zinc-400">
                <div className="flex items-center gap-2">
                  <MapPin className="w-3 h-3" />
                  <span>{accident.location}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-3 h-3" />
                  <span>{format(new Date(accident.timestamp), "MMM dd, yyyy")}</span>
                </div>
              </div>

              {accident.details && (
                <p className="text-xs text-zinc-500 mt-2 border-t border-zinc-800 pt-2">
                  {accident.details}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
