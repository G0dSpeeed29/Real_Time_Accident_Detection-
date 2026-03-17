import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/App";
import Sidebar from "@/components/Sidebar";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { TrendingUp, AlertTriangle, Clock, MapPin } from "lucide-react";
import { toast } from "sonner";

const SEVERITY_COLORS = {
  low: "#22c55e",
  medium: "#eab308",
  high: "#f97316",
  critical: "#ef4444"
};

export default function Analytics() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [accidents, setAccidents] = useState([]);

  useEffect(() => {
    fetchStats();
    fetchAccidents();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/analytics/stats`);
      setStats(response.data);
    } catch (error) {
      toast.error("Failed to fetch analytics");
    }
  };

  const fetchAccidents = async () => {
    try {
      const response = await axios.get(`${API}/accidents?limit=100`);
      setAccidents(response.data);
    } catch (error) {
      console.error("Failed to fetch accidents:", error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  const severityData = stats ? [
    { name: "Low", value: stats.severity_distribution.low, color: SEVERITY_COLORS.low },
    { name: "Medium", value: stats.severity_distribution.medium, color: SEVERITY_COLORS.medium },
    { name: "High", value: stats.severity_distribution.high, color: SEVERITY_COLORS.high },
    { name: "Critical", value: stats.severity_distribution.critical, color: SEVERITY_COLORS.critical }
  ] : [];

  return (
    <div className="flex min-h-screen bg-zinc-950" data-testid="analytics-page">
      <Sidebar onLogout={handleLogout} />
      
      <div className="flex-1 ml-16 p-6">
        <div className="mb-6">
          <h1 className="text-4xl font-bold uppercase tracking-tight" data-testid="analytics-title">Analytics</h1>
          <p className="text-zinc-400 mt-1">Statistical insights and trends</p>
        </div>

        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="stats-card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-zinc-500 uppercase tracking-wide">Total Accidents</span>
                <AlertTriangle className="w-5 h-5 text-red-500" />
              </div>
              <p className="text-3xl font-bold" data-testid="total-accidents">{stats.total_accidents}</p>
            </div>

            <div className="stats-card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-zinc-500 uppercase tracking-wide">Today</span>
                <Clock className="w-5 h-5 text-blue-500" />
              </div>
              <p className="text-3xl font-bold" data-testid="today-accidents">{stats.today_accidents}</p>
            </div>

            <div className="stats-card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-zinc-500 uppercase tracking-wide">This Week</span>
                <TrendingUp className="w-5 h-5 text-green-500" />
              </div>
              <p className="text-3xl font-bold" data-testid="week-accidents">{stats.week_accidents}</p>
            </div>

            <div className="stats-card">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-zinc-500 uppercase tracking-wide">Active Sources</span>
                <MapPin className="w-5 h-5 text-yellow-500" />
              </div>
              <p className="text-3xl font-bold" data-testid="active-sources">{stats.active_sources}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass-card p-6">
            <h2 className="text-2xl font-semibold mb-4" data-testid="severity-chart-title">Severity Distribution</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={severityData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => entry.name}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {severityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#18181b",
                    border: "1px solid #3f3f46",
                    borderRadius: "6px",
                    color: "#fafafa"
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            
            <div className="grid grid-cols-2 gap-3 mt-4">
              {severityData.map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                  <span className="text-sm text-zinc-400">{item.name}: {item.value}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card p-6">
            <h2 className="text-2xl font-semibold mb-4" data-testid="recent-activity-title">Recent Activity</h2>
            <div className="space-y-3 max-h-[400px] overflow-y-auto scrollbar-thin pr-2">
              {accidents.slice(0, 10).map((accident) => (
                <div key={accident.id} className="stats-card" data-testid={`activity-item-${accident.id}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`severity-badge severity-${accident.severity}`}>
                          {accident.severity}
                        </span>
                      </div>
                      <p className="text-sm font-medium">{accident.accident_type}</p>
                      <p className="text-xs text-zinc-500 mt-1">{accident.location}</p>
                    </div>
                    <span className="text-xs text-zinc-500 font-mono whitespace-nowrap ml-2">
                      {new Date(accident.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
