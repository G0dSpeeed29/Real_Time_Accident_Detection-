import { Activity, AlertTriangle, Clock, Video } from "lucide-react";

export default function StatsStrip({ stats }) {
  if (!stats) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4" data-testid="stats-strip-loading">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="stats-card animate-pulse">
            <div className="h-4 bg-zinc-800 rounded mb-3 w-24"></div>
            <div className="h-8 bg-zinc-800 rounded w-16"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4" data-testid="stats-strip">
      <div className="stats-card">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-zinc-500 uppercase tracking-wide">Total Accidents</span>
          <AlertTriangle className="w-5 h-5 text-red-500" />
        </div>
        <p className="text-3xl font-bold" data-testid="stat-total">{stats.total_accidents}</p>
        <p className="text-xs text-zinc-600 mt-1">All time</p>
      </div>

      <div className="stats-card">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-zinc-500 uppercase tracking-wide">Today</span>
          <Clock className="w-5 h-5 text-blue-500" />
        </div>
        <p className="text-3xl font-bold" data-testid="stat-today">{stats.today_accidents}</p>
        <p className="text-xs text-zinc-600 mt-1">Last 24 hours</p>
      </div>

      <div className="stats-card">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-zinc-500 uppercase tracking-wide">This Week</span>
          <Activity className="w-5 h-5 text-green-500" />
        </div>
        <p className="text-3xl font-bold" data-testid="stat-week">{stats.week_accidents}</p>
        <p className="text-xs text-zinc-600 mt-1">Last 7 days</p>
      </div>

      <div className="stats-card">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-zinc-500 uppercase tracking-wide">Active Sources</span>
          <Video className="w-5 h-5 text-yellow-500" />
        </div>
        <p className="text-3xl font-bold" data-testid="stat-sources">{stats.active_sources}</p>
        <p className="text-xs text-zinc-600 mt-1">Monitoring now</p>
      </div>
    </div>
  );
}
