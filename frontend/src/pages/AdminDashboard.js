import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/App";
import Sidebar from "@/components/Sidebar";
import VideoFeed from "@/components/VideoFeed";
import AlertsPanel from "@/components/AlertsPanel";
import StatsStrip from "@/components/StatsStrip";
import { toast } from "sonner";

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [videoSources, setVideoSources] = useState([]);
  const [accidents, setAccidents] = useState([]);
  const [stats, setStats] = useState(null);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    if (user.role !== "admin") {
      navigate("/emergency");
    }

    fetchVideoSources();
    fetchAccidents();
    fetchStats();
    connectWebSocket();

    return () => {
      if (ws) ws.close();
    };
  }, []);

  const connectWebSocket = () => {
    const wsUrl = API.replace("https://", "wss://").replace("http://", "ws://");
    const socket = new WebSocket(`${wsUrl}/ws/detection`);

    socket.onopen = () => {
      console.log("WebSocket connected");
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === "accident_detected") {
        setAccidents(prev => [data.accident, ...prev]);
        toast.error("⚠️ ACCIDENT DETECTED!", {
          description: `${data.accident.location} - ${data.accident.severity.toUpperCase()}`
        });
        playAlertSound();
      }
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    setWs(socket);
  };

  const playAlertSound = () => {
    const audio = new Audio("data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBTGH0fPTgjMGHm7A7+OZURE");
    audio.play().catch(() => {});
  };

  const fetchVideoSources = async () => {
    try {
      const response = await axios.get(`${API}/video-sources`);
      setVideoSources(response.data);
    } catch (error) {
      console.error("Failed to fetch video sources:", error);
    }
  };

  const fetchAccidents = async () => {
    try {
      const response = await axios.get(`${API}/accidents?limit=10`);
      setAccidents(response.data);
    } catch (error) {
      console.error("Failed to fetch accidents:", error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/analytics/stats`);
      setStats(response.data);
    } catch (error) {
      console.error("Failed to fetch stats:", error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  return (
    <div className="flex min-h-screen bg-zinc-950" data-testid="admin-dashboard">
      <Sidebar onLogout={handleLogout} />
      
      <div className="flex-1 ml-16 p-6">
        <div className="mb-6">
          <h1 className="text-4xl font-bold uppercase tracking-tight" data-testid="dashboard-title">Command Center</h1>
          <p className="text-zinc-400 mt-1">Real-time accident monitoring & detection</p>
        </div>

        <StatsStrip stats={stats} />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-semibold" data-testid="live-feeds-title">Live Feeds</h2>
                <button
                  onClick={() => navigate("/settings")}
                  data-testid="add-source-button"
                  className="btn-primary px-4 py-2 text-sm"
                >
                  + Add Source
                </button>
              </div>
              
              {videoSources.length === 0 ? (
                <div className="text-center py-12 text-zinc-500" data-testid="no-sources-message">
                  <p>No video sources configured. Add a source to start monitoring.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4">
                  {videoSources.map((source) => (
                    <VideoFeed key={source.id} source={source} onRefresh={fetchVideoSources} />
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-1">
            <AlertsPanel accidents={accidents} />
          </div>
        </div>
      </div>
    </div>
  );
}
