import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { API } from "@/App";
import { Play, Square, Upload, Camera } from "lucide-react";
import { toast } from "sonner";

export default function VideoFeed({ source, onRefresh }) {
  const [isDetecting, setIsDetecting] = useState(source.status === "active");
  const [uploading, setUploading] = useState(false);
  const [frameData, setFrameData] = useState(null);
  const [connected, setConnected] = useState(false);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (isDetecting) {
      connectWebSocket();
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [isDetecting, source.id]);

  useEffect(() => {
    if (frameData && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      const img = new Image();
      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        
        // Draw detection boxes if available
        if (frameData.detections && frameData.detections.length > 0) {
          frameData.detections.forEach(det => {
            const [x1, y1, x2, y2] = det.bbox;
            ctx.strokeStyle = '#ef4444';
            ctx.lineWidth = 3;
            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
            
            // Draw label
            ctx.fillStyle = '#ef4444';
            ctx.fillRect(x1, y1 - 25, 150, 25);
            ctx.fillStyle = '#ffffff';
            ctx.font = '14px Arial';
            ctx.fillText(`${det.class} ${(det.confidence * 100).toFixed(0)}%`, x1 + 5, y1 - 7);
          });
        }
      };
      img.src = `data:image/jpeg;base64,${frameData.frame}`;
    }
  }, [frameData]);

  const connectWebSocket = () => {
    const wsUrl = API.replace("https://", "wss://").replace("http://", "ws://");
    const ws = new WebSocket(`${wsUrl}/ws/detection`);

    ws.onopen = () => {
      console.log("WebSocket connected for video feed");
      setConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "detection_frame" && data.source_id === source.id) {
        setFrameData(data);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setConnected(false);
    };

    ws.onclose = () => {
      setConnected(false);
    };

    wsRef.current = ws;
  };

  const handleStartDetection = async () => {
    try {
      await axios.post(`${API}/detection/start/${source.id}`);
      toast.success("Detection started");
      setIsDetecting(true);
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to start detection");
      console.error("Start detection error:", error);
    }
  };

  const handleStopDetection = async () => {
    try {
      await axios.post(`${API}/detection/stop/${source.id}`);
      toast.success("Detection stopped");
      setIsDetecting(false);
      setFrameData(null);
      if (wsRef.current) {
        wsRef.current.close();
      }
      onRefresh();
    } catch (error) {
      toast.error("Failed to stop detection");
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(`${API}/detection/upload-video`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      toast.success("Video uploaded successfully");
      
      // Update video source with the uploaded file path
      await axios.patch(`${API}/video-sources/${source.id}`, {
        url: response.data.file_path
      });
      
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload video");
      console.error("Upload error:", error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="video-container group" data-testid={`video-feed-${source.id}`}>
      {/* Video display area */}
      <div className="absolute inset-0 bg-black flex items-center justify-center">
        {isDetecting ? (
          <canvas 
            ref={canvasRef}
            className="w-full h-full object-contain"
            data-testid={`video-canvas-${source.id}`}
          />
        ) : (
          <>
            <img
              src="https://images.unsplash.com/photo-1580035144415-01307b0e464a?crop=entropy&cs=srgb&fm=jpg&q=85"
              alt="CCTV Feed"
              className="w-full h-full object-cover opacity-30"
            />
            <div className="absolute flex flex-col items-center justify-center">
              <Camera className="w-16 h-16 text-zinc-600 mb-3" />
              <p className="text-zinc-500 text-sm">
                Click Start to begin detection
              </p>
            </div>
          </>
        )}
        
        {isDetecting && !frameData && (
          <div className="absolute flex flex-col items-center justify-center">
            <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mb-3"></div>
            <p className="text-zinc-400 text-sm">Connecting to video stream...</p>
          </div>
        )}
      </div>

      {/* Status indicator */}
      <div className="absolute top-3 left-3 flex items-center gap-2 bg-black/70 px-3 py-1.5 rounded-md backdrop-blur-sm">
        {isDetecting && <div className="live-dot"></div>}
        <span className="text-sm font-semibold uppercase tracking-wide">
          {isDetecting ? "LIVE" : "OFFLINE"}
        </span>
        {isDetecting && connected && (
          <span className="text-xs text-green-400">• Connected</span>
        )}
      </div>

      {/* Controls */}
      <div className="absolute bottom-3 left-3 right-3 bg-black/70 px-4 py-3 rounded-md backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold" data-testid={`source-name-${source.id}`}>{source.name}</h3>
            <p className="text-xs text-zinc-400">{source.location}</p>
            <p className="text-xs text-zinc-600 mt-1">Type: {source.type.toUpperCase()}</p>
          </div>
          
          <div className="flex items-center gap-2">
            {source.type === "file" && (
              <label className="btn-secondary px-3 py-1.5 text-xs cursor-pointer flex items-center gap-1">
                <Upload className="w-3 h-3" />
                {uploading ? "Uploading..." : "Upload"}
                <input
                  type="file"
                  accept="video/*"
                  className="hidden"
                  onChange={handleFileUpload}
                  disabled={uploading}
                  data-testid={`upload-video-${source.id}`}
                />
              </label>
            )}
            
            {!isDetecting ? (
              <button
                onClick={handleStartDetection}
                data-testid={`start-detection-${source.id}`}
                className="btn-primary px-3 py-1.5 text-xs flex items-center gap-1"
              >
                <Play className="w-3 h-3" />
                Start
              </button>
            ) : (
              <button
                onClick={handleStopDetection}
                data-testid={`stop-detection-${source.id}`}
                className="bg-zinc-700 hover:bg-zinc-600 text-white px-3 py-1.5 rounded-md text-xs flex items-center gap-1 transition-colors"
              >
                <Square className="w-3 h-3" />
                Stop
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
