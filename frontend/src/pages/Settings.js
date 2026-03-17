import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/App";
import Sidebar from "@/components/Sidebar";
import { Plus, Trash2, Video, Webcam, Link as LinkIcon } from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";

export default function Settings() {
  const navigate = useNavigate();
  const [videoSources, setVideoSources] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    type: "youtube",
    url: "",
    location: ""
  });

  useEffect(() => {
    fetchVideoSources();
  }, []);

  const fetchVideoSources = async () => {
    try {
      const response = await axios.get(`${API}/video-sources`);
      setVideoSources(response.data);
    } catch (error) {
      toast.error("Failed to fetch video sources");
    }
  };

  const handleAddSource = async (e) => {
    e.preventDefault();
    
    try {
      await axios.post(`${API}/video-sources`, formData);
      toast.success("Video source added successfully");
      setFormData({ name: "", type: "youtube", url: "", location: "" });
      setShowAddForm(false);
      fetchVideoSources();
    } catch (error) {
      toast.error("Failed to add video source");
    }
  };

  const handleDeleteSource = async (sourceId) => {
    if (!confirm("Are you sure you want to delete this video source?")) {
      return;
    }

    try {
      await axios.delete(`${API}/video-sources/${sourceId}`);
      toast.success("Video source deleted");
      fetchVideoSources();
    } catch (error) {
      toast.error("Failed to delete video source");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  };

  const getSourceIcon = (type) => {
    switch (type) {
      case "webcam": return <Webcam className="w-5 h-5" />;
      case "rtsp": return <LinkIcon className="w-5 h-5" />;
      case "youtube": return <Video className="w-5 h-5 text-red-500" />;
      case "file": return <Video className="w-5 h-5" />;
      default: return <Video className="w-5 h-5" />;
    }
  };

  return (
    <div className="flex min-h-screen bg-zinc-950" data-testid="settings-page">
      <Sidebar onLogout={handleLogout} />
      
      <div className="flex-1 ml-16 p-6">
        <div className="mb-6">
          <h1 className="text-4xl font-bold uppercase tracking-tight" data-testid="settings-title">Settings</h1>
          <p className="text-zinc-400 mt-1">Manage video sources and system configuration</p>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-semibold" data-testid="video-sources-title">Video Sources</h2>
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              data-testid="toggle-add-form-button"
              className="btn-primary px-4 py-2 flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add Source
            </button>
          </div>

          {showAddForm && (
            <form onSubmit={handleAddSource} className="glass-card p-4 mb-6" data-testid="add-source-form">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Source Name</label>
                  <input
                    type="text"
                    data-testid="source-name-input"
                    placeholder="e.g., Main Street Camera"
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Type</label>
                  <select
                    data-testid="source-type-select"
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                  >
                    <option value="youtube">YouTube Live Stream</option>
                    <option value="rtsp">RTSP Stream</option>
                    <option value="webcam">Webcam</option>
                    <option value="file">Video File</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">URL / Path</label>
                  <input
                    type="text"
                    data-testid="source-url-input"
                    placeholder={
                      formData.type === "youtube" ? "YouTube live stream URL (e.g., https://www.youtube.com/live/...)" :
                      formData.type === "rtsp" ? "rtsp://... or http://..." :
                      formData.type === "webcam" ? "0 for default webcam" :
                      "/path/to/video.mp4"
                    }
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  />
                  {formData.type === "youtube" && (
                    <p className="text-xs text-zinc-500 mt-1">Paste the full YouTube live stream URL</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Location</label>
                  <input
                    type="text"
                    data-testid="source-location-input"
                    placeholder="e.g., Main Street & 5th Ave"
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="flex gap-2 mt-4">
                <button type="submit" data-testid="submit-source-button" className="btn-primary px-6 py-2">
                  Add Source
                </button>
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  data-testid="cancel-add-button"
                  className="btn-secondary px-6 py-2"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="space-y-3">
            {videoSources.length === 0 ? (
              <div className="text-center py-8 text-zinc-500" data-testid="no-sources-message">
                <p>No video sources configured. Click "Add Source" to get started.</p>
              </div>
            ) : (
              videoSources.map((source) => (
                <div key={source.id} className="stats-card" data-testid={`source-item-${source.id}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 flex-1">
                      <div className="p-3 bg-zinc-900 rounded-lg">
                        {getSourceIcon(source.type)}
                      </div>
                      
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg">{source.name}</h3>
                        <p className="text-sm text-zinc-500">{source.location}</p>
                        <div className="flex items-center gap-3 mt-1">
                          <span className="text-xs px-2 py-1 bg-zinc-800 rounded">{source.type.toUpperCase()}</span>
                          <span className={`text-xs px-2 py-1 rounded ${
                            source.status === "active" ? "bg-green-500/20 text-green-400" :
                            source.status === "error" ? "bg-red-500/20 text-red-400" :
                            "bg-zinc-700 text-zinc-400"
                          }`}>
                            {source.status}
                          </span>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeleteSource(source.id)}
                      data-testid={`delete-source-${source.id}`}
                      className="p-2 text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
