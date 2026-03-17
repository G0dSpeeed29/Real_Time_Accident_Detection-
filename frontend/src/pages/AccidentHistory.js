import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/App";
import Sidebar from "@/components/Sidebar";
import { Search, Filter, Download } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";

export default function AccidentHistory() {
  const navigate = useNavigate();
  const [accidents, setAccidents] = useState([]);
  const [filteredAccidents, setFilteredAccidents] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    fetchAccidents();
  }, []);

  useEffect(() => {
    filterAccidents();
  }, [searchTerm, severityFilter, statusFilter, accidents]);

  const fetchAccidents = async () => {
    try {
      const response = await axios.get(`${API}/accidents?limit=500`);
      setAccidents(response.data);
    } catch (error) {
      toast.error("Failed to fetch accident history");
    }
  };

  const filterAccidents = () => {
    let filtered = [...accidents];

    if (searchTerm) {
      filtered = filtered.filter(acc => 
        acc.location.toLowerCase().includes(searchTerm.toLowerCase()) ||
        acc.accident_type.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (severityFilter !== "all") {
      filtered = filtered.filter(acc => acc.severity === severityFilter);
    }

    if (statusFilter !== "all") {
      filtered = filtered.filter(acc => acc.status === statusFilter);
    }

    setFilteredAccidents(filtered);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  return (
    <div className="flex min-h-screen bg-zinc-950" data-testid="accident-history-page">
      <Sidebar onLogout={handleLogout} />
      
      <div className="flex-1 ml-16 p-6">
        <div className="mb-6">
          <h1 className="text-4xl font-bold uppercase tracking-tight" data-testid="history-title">Accident History</h1>
          <p className="text-zinc-400 mt-1">Comprehensive log of all detected incidents</p>
        </div>

        <div className="glass-card p-6 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
              <input
                type="text"
                placeholder="Search by location or type..."
                data-testid="search-input"
                className="w-full pl-10 bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all placeholder:text-zinc-600"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              data-testid="severity-filter"
              className="bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            >
              <option value="all">All Severities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              data-testid="status-filter"
              className="bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            >
              <option value="all">All Status</option>
              <option value="new">New</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>

        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="accidents-table">
              <thead className="bg-zinc-900/50 border-b border-zinc-800">
                <tr>
                  <th className="text-left px-4 py-3 text-sm font-semibold uppercase tracking-wide">Time</th>
                  <th className="text-left px-4 py-3 text-sm font-semibold uppercase tracking-wide">Type</th>
                  <th className="text-left px-4 py-3 text-sm font-semibold uppercase tracking-wide">Location</th>
                  <th className="text-left px-4 py-3 text-sm font-semibold uppercase tracking-wide">Severity</th>
                  <th className="text-left px-4 py-3 text-sm font-semibold uppercase tracking-wide">Status</th>
                  <th className="text-left px-4 py-3 text-sm font-semibold uppercase tracking-wide">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {filteredAccidents.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="text-center py-8 text-zinc-500">
                      No accidents found
                    </td>
                  </tr>
                ) : (
                  filteredAccidents.map((accident) => (
                    <tr key={accident.id} className="hover:bg-zinc-900/30 transition-colors" data-testid={`accident-row-${accident.id}`}>
                      <td className="px-4 py-3 text-sm font-mono">
                        {format(new Date(accident.timestamp), "MMM dd, HH:mm:ss")}
                      </td>
                      <td className="px-4 py-3 text-sm">{accident.accident_type}</td>
                      <td className="px-4 py-3 text-sm">{accident.location}</td>
                      <td className="px-4 py-3">
                        <span className={`severity-badge severity-${accident.severity}`}>
                          {accident.severity}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          accident.status === "new" ? "bg-red-500/20 text-red-400" :
                          accident.status === "acknowledged" ? "bg-yellow-500/20 text-yellow-400" :
                          "bg-green-500/20 text-green-400"
                        }`}>
                          {accident.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-zinc-400">{accident.source_name}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-4 text-center text-sm text-zinc-500" data-testid="results-count">
          Showing {filteredAccidents.length} of {accidents.length} accidents
        </div>
      </div>
    </div>
  );
}
