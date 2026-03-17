import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/App";
import Sidebar from "@/components/Sidebar";
import { Clock, MapPin, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";

export default function EmergencyDashboard() {
  const navigate = useNavigate();
  const [accidents, setAccidents] = useState([]);
  const [selectedAccident, setSelectedAccident] = useState(null);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    if (user.role !== "emergency_services") {
      navigate("/admin");
    }

    fetchAccidents();
    connectWebSocket();

    return () => {
      if (ws) ws.close();
    };
  }, []);

  const connectWebSocket = () => {
    const wsUrl = API.replace("https://", "wss://").replace("http://", "ws://");
    const socket = new WebSocket(`${wsUrl}/ws/detection`);

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "accident_detected") {
        setAccidents(prev => [data.accident, ...prev]);
        toast.error("🚨 New Accident Reported!", {
          description: data.accident.location
        });
        playAlertSound();
      }
    };

    setWs(socket);
  };

  const playAlertSound = () => {
    const audio = new Audio("data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBTGH0fPTgjMGHm7A7+OZURE");
    audio.play().catch(() => {});
  };

  const fetchAccidents = async () => {
    try {
      const response = await axios.get(`${API}/accidents?limit=50`);
      setAccidents(response.data);
    } catch (error) {
      console.error("Failed to fetch accidents:", error);
    }
  };

  const handleAcknowledge = async (accidentId) => {
    try {
      await axios.patch(`${API}/accidents/${accidentId}`, { status: "acknowledged" });
      toast.success("Accident acknowledged");
      fetchAccidents();
    } catch (error) {
      toast.error("Failed to update accident status");
    }
  };

  const handleResolve = async (accidentId) => {
    try {
      await axios.patch(`${API}/accidents/${accidentId}`, { status: "resolved" });
      toast.success("Accident marked as resolved");
      fetchAccidents();
    } catch (error) {
      toast.error("Failed to update accident status");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  return (
    <div className="flex min-h-screen bg-zinc-950" data-testid="emergency-dashboard">
      <Sidebar onLogout={handleLogout} />
      
      <div className="flex-1 ml-16 p-6">
        <div className="mb-6">
          <h1 className="text-4xl font-bold uppercase tracking-tight" data-testid="emergency-title">Emergency Response</h1>
          <p className="text-zinc-400 mt-1">Active incident monitoring and response</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h2 className="text-2xl font-semibold mb-4" data-testid="incidents-list-title">Active Incidents</h2>
            
            {accidents.length === 0 ? (
              <div className="glass-card p-8 text-center text-zinc-500" data-testid="no-incidents-message">
                <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No incidents reported</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[calc(100vh-200px)] overflow-y-auto scrollbar-thin pr-2">
                {accidents.map((accident) => (
                  <div
                    key={accident.id}
                    data-testid={`accident-card-${accident.id}`}
                    className={`cursor-pointer transition-all ${
                      accident.status === "new" ? "alert-card" : "glass-card"
                    } p-4 hover:border-blue-500`}
                    onClick={() => setSelectedAccident(accident)}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-red-500" />
                        <span className={`severity-badge severity-${accident.severity}`}>
                          {accident.severity}
                        </span>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        accident.status === "new" ? "bg-red-500/20 text-red-400" :
                        accident.status === "acknowledged" ? "bg-yellow-500/20 text-yellow-400" :
                        "bg-green-500/20 text-green-400"
                      }`}>
                        {accident.status}
                      </span>
                    </div>
                    
                    <h3 className="font-semibold mb-2">{accident.accident_type}</h3>
                    
                    <div className="space-y-1 text-sm text-zinc-400">
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4" />
                        <span>{accident.location}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        <span className="font-mono">
                          {format(new Date(accident.timestamp), "MMM dd, yyyy HH:mm:ss")}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            {selectedAccident ? (
              <div className="glass-card p-6" data-testid="incident-details">
                <h2 className="text-2xl font-semibold mb-4">Incident Details</h2>
                
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-zinc-500 uppercase tracking-wide">Type</label>
                    <p className="text-lg font-medium">{selectedAccident.accident_type}</p>
                  </div>
                  
                  <div>
                    <label className="text-sm text-zinc-500 uppercase tracking-wide">Severity</label>
                    <div className="mt-1">
                      <span className={`severity-badge severity-${selectedAccident.severity}`}>
                        {selectedAccident.severity}
                      </span>
                    </div>
                  </div>
                  
                  <div>
                    <label className="text-sm text-zinc-500 uppercase tracking-wide">Location</label>
                    <p className="text-lg flex items-center gap-2">
                      <MapPin className="w-4 h-4" />
                      {selectedAccident.location}
                    </p>
                  </div>
                  
                  <div>
                    <label className="text-sm text-zinc-500 uppercase tracking-wide">Time</label>
                    <p className="text-lg font-mono">
                      {format(new Date(selectedAccident.timestamp), "MMM dd, yyyy HH:mm:ss")}
                    </p>
                  </div>
                  
                  <div>
                    <label className="text-sm text-zinc-500 uppercase tracking-wide">Source</label>
                    <p className="text-lg">{selectedAccident.source_name}</p>
                  </div>
                  
                  <div>
                    <label className="text-sm text-zinc-500 uppercase tracking-wide">Confidence</label>
                    <p className="text-lg">{(selectedAccident.confidence * 100).toFixed(1)}%</p>
                  </div>
                  
                  {selectedAccident.details && (
                    <div>
                      <label className="text-sm text-zinc-500 uppercase tracking-wide">Details</label>
                      <p className="text-sm text-zinc-300">{selectedAccident.details}</p>
                    </div>
                  )}
                  
                  <div className="pt-4 space-y-2">
                    {selectedAccident.status === "new" && (
                      <button
                        onClick={() => handleAcknowledge(selectedAccident.id)}
                        data-testid="acknowledge-button"
                        className="w-full btn-primary py-2.5"
                      >
                        Acknowledge Incident
                      </button>
                    )}
                    {selectedAccident.status === "acknowledged" && (
                      <button
                        onClick={() => handleResolve(selectedAccident.id)}
                        data-testid="resolve-button"
                        className="w-full bg-green-600 hover:bg-green-700 text-white font-medium rounded-md py-2.5 transition-colors"
                      >
                        Mark as Resolved
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="glass-card p-8 text-center text-zinc-500 h-full flex items-center justify-center">
                <p>Select an incident to view details</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
