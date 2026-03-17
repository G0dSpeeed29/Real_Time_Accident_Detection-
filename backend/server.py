from fastapi import FastAPI, APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import json
import asyncio
import cv2
import numpy as np
from ultralytics import YOLO
import base64
from collections import defaultdict
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yt_dlp
from twilio.rest import Client
import bcrypt
import subprocess
import threading
import time

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get("SECRET_KEY", "accident-detection-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

VIDEO_STORAGE_DIR = ROOT_DIR / "video_clips"
VIDEO_STORAGE_DIR.mkdir(exist_ok=True)

# Email configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "alerts@example.com")

# Twilio SMS configuration
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")
ALERT_PHONE_NUMBER = os.environ.get("ALERT_PHONE_NUMBER", "")

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    role: Literal["admin", "emergency_services"]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: Literal["admin", "emergency_services"] = "emergency_services"

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class VideoSource(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: Literal["rtsp", "webcam", "file", "youtube"]
    url: Optional[str] = None
    status: Literal["active", "inactive", "error"] = "inactive"
    location: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VideoSourceCreate(BaseModel):
    name: str
    type: Literal["rtsp", "webcam", "file", "youtube"]
    url: Optional[str] = None
    location: Optional[str] = None

class Accident(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    location: str
    severity: Literal["low", "medium", "high", "critical"]
    accident_type: str
    video_clip_path: Optional[str] = None
    snapshot_path: Optional[str] = None
    source_id: str
    source_name: str
    confidence: float
    details: Optional[str] = None
    status: Literal["new", "acknowledged", "resolved"] = "new"

class AccidentUpdate(BaseModel):
    status: Optional[Literal["new", "acknowledged", "resolved"]] = None
    details: Optional[str] = None

class DetectionFrame(BaseModel):
    source_id: str
    timestamp: str
    detections: List[dict]
    frame_base64: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

try:
    yolo_model = YOLO('yolov8n.pt')
    logging.info("YOLOv8 model loaded successfully")
except Exception as e:
    logging.error(f"Failed to load YOLOv8 model: {e}")
    yolo_model = None

active_streams = {}

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    # If using bcrypt directly
    try:
        if isinstance(plain_password, str):
            plain_password = plain_password.encode('utf-8')
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception as e:
        logging.error(f"Password verification error: {e}")
        # Fallback to passlib if it's an old hash format
        try:
            return pwd_context.verify(plain_password.decode('utf-8'), hashed_password.decode('utf-8'))
        except:
            return False

def get_password_hash(password):
    if isinstance(password, str):
        password = password.encode('utf-8')
    hashed = bcrypt.hashpw(password, bcrypt.gensalt())
    return hashed.decode('utf-8')

def send_email_alert(accident: Accident):
    """Send email alert for detected accident"""
    try:
        # Create demo email content
        subject = f"🚨 ACCIDENT ALERT - {accident.severity.upper()} Severity"
        
        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
              <h2 style="color: #ef4444; border-bottom: 2px solid #ef4444; padding-bottom: 10px;">⚠️ Accident Detected</h2>
              
              <div style="margin: 20px 0;">
                <p><strong>Severity:</strong> <span style="background-color: #fee; color: #ef4444; padding: 4px 12px; border-radius: 16px; text-transform: uppercase;">{accident.severity}</span></p>
                <p><strong>Type:</strong> {accident.accident_type}</p>
                <p><strong>Location:</strong> {accident.location}</p>
                <p><strong>Time:</strong> {accident.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Source:</strong> {accident.source_name}</p>
                <p><strong>Confidence:</strong> {accident.confidence * 100:.1f}%</p>
              </div>
              
              {f'<div style="background-color: #f9f9f9; padding: 15px; border-radius: 4px; margin: 15px 0;"><p><strong>Details:</strong></p><p>{accident.details}</p></div>' if accident.details else ''}
              
              <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; color: #666; font-size: 12px;">
                <p>This is an automated alert from the Accident Detection System.</p>
                <p>Please respond to this incident through the emergency dashboard.</p>
              </div>
            </div>
          </body>
        </html>
        """
        
        # Log email content (for demo purposes - in production, actually send via SMTP)
        logging.info(f"✉️ EMAIL ALERT: {subject}")
        logging.info(f"To: {ALERT_EMAIL}")
        logging.info(f"Accident ID: {accident.id}")
        logging.info(f"Location: {accident.location}")
        logging.info(f"Severity: {accident.severity}")
        
        # If SMTP credentials are configured, actually send the email
        if SMTP_USERNAME and SMTP_PASSWORD:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = SMTP_USERNAME
            msg['To'] = ALERT_EMAIL
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
            
            logging.info(f"✅ Email alert sent successfully to {ALERT_EMAIL}")
        else:
            logging.info("📧 Email credentials not configured - alert logged only")
            
    except Exception as e:
        logging.error(f"❌ Failed to send email alert: {e}")

def send_sms_alert(accident: Accident):
    """Send SMS alert via Twilio"""
    try:
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, ALERT_PHONE_NUMBER]):
            logging.info("📱 Twilio credentials not configured - SMS alert skipped")
            return
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message_body = f"""
🚨 ACCIDENT ALERT

Severity: {accident.severity.upper()}
Location: {accident.location}
Time: {accident.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Type: {accident.accident_type}

Check dashboard for details.
        """.strip()
        
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=ALERT_PHONE_NUMBER
        )
        
        logging.info(f"📱 SMS ALERT sent successfully. SID: {message.sid}")
        logging.info(f"To: {ALERT_PHONE_NUMBER}")
        logging.info(f"Location: {accident.location}")
        logging.info(f"Severity: {accident.severity}")
        
    except Exception as e:
        logging.error(f"❌ Failed to send SMS alert: {e}")

def extract_youtube_stream(youtube_url: str) -> tuple[str, dict]:
    """
    Extract a playable YouTube URL plus the HTTP headers needed to fetch it.

    For live streams YouTube frequently returns HLS/DASH URLs that require headers
    (UA/Referer/Cookie) to load the media segments. We pass these headers to ffmpeg.
    """
    try:
        ydl_opts = {
            # Allow yt-dlp to pick the best available; for live this is often HLS.
            # We'll rely on ffmpeg to decode, with headers from yt-dlp.
            "format": "best",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

        if not info or not isinstance(info, dict):
            raise Exception("yt-dlp returned no info")

        stream_url = info.get("url")
        if not stream_url and info.get("formats"):
            # Prefer formats that provide a direct URL
            for fmt in reversed(info.get("formats") or []):
                if fmt.get("url"):
                    stream_url = fmt["url"]
                    break
        if not stream_url:
            raise Exception("No stream URL found")

        http_headers = info.get("http_headers") or {}
        # Ensure the headers we usually need for googlevideo segment fetches exist.
        if "User-Agent" not in http_headers and info.get("user_agent"):
            http_headers["User-Agent"] = info["user_agent"]
        if "Referer" not in http_headers:
            http_headers["Referer"] = "https://www.youtube.com/"

        logging.info("📺 YouTube: stream URL extracted")
        return stream_url, http_headers
    except Exception as e:
        logging.error(f"❌ Failed to extract YouTube stream: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract YouTube stream: {str(e)}")

async def get_current_user(token: str):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if user is None:
        raise credentials_exception
    return User(**user)

@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate):
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_data.email,
        name=user_data.name,
        role=user_data.role
    )
    
    user_dict = user.model_dump()
    user_dict["password"] = get_password_hash(user_data.password)
    user_dict["created_at"] = user_dict["created_at"].isoformat()
    
    await db.users.insert_one(user_dict)
    return user

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user_doc or not verify_password(credentials.password, user_doc.get("password", "")):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user_doc["email"]})
    
    user_doc.pop("password", None)
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=User(**user_doc)
    )

@api_router.get("/video-sources", response_model=List[VideoSource])
async def get_video_sources():
    sources = await db.video_sources.find({}, {"_id": 0}).to_list(1000)
    for source in sources:
        if isinstance(source.get('created_at'), str):
            source['created_at'] = datetime.fromisoformat(source['created_at'])
    return sources

@api_router.post("/video-sources", response_model=VideoSource)
async def create_video_source(source_data: VideoSourceCreate):
    source = VideoSource(**source_data.model_dump())
    
    # If it's a YouTube source, extract the stream URL
    if source.type == "youtube" and source.url:
        try:
            stream_url, http_headers = extract_youtube_stream(source.url)
            # Keep the original YouTube URL and store derived stream URL separately.
            # (Direct stream URLs can expire; we also use ffmpeg for playback.)
            logging.info(f"Extracted YouTube stream URL: {stream_url[:100]}...")
        except Exception as e:
            logging.error(f"Failed to extract YouTube URL: {e}")
            raise HTTPException(status_code=400, detail="Failed to extract YouTube stream URL")
    
    source_dict = source.model_dump()
    source_dict["created_at"] = source_dict["created_at"].isoformat()
    if source.type == "youtube" and source.url:
        source_dict["stream_url"] = stream_url
        source_dict["stream_headers"] = http_headers
    await db.video_sources.insert_one(source_dict)
    return source

@api_router.patch("/video-sources/{source_id}", response_model=VideoSource)
async def update_video_source(source_id: str, update_data: dict):
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    result = await db.video_sources.update_one(
        {"id": source_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Video source not found")
    
    source = await db.video_sources.find_one({"id": source_id}, {"_id": 0})
    if isinstance(source.get('created_at'), str):
        source['created_at'] = datetime.fromisoformat(source['created_at'])
    return VideoSource(**source)

@api_router.delete("/video-sources/{source_id}")
async def delete_video_source(source_id: str):
    # Stop detection if active
    if source_id in active_streams:
        try:
            active_streams[source_id].cancel()
            del active_streams[source_id]
        except:
            pass
    
    result = await db.video_sources.delete_one({"id": source_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Video source not found")
    
    logging.info(f"Video source {source_id} deleted successfully")
    return {"message": "Video source deleted successfully"}

@api_router.get("/accidents", response_model=List[Accident])
async def get_accidents(limit: int = 100, status: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    
    accidents = await db.accidents.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    for accident in accidents:
        if isinstance(accident.get('timestamp'), str):
            accident['timestamp'] = datetime.fromisoformat(accident['timestamp'])
    return accidents

@api_router.get("/accidents/{accident_id}", response_model=Accident)
async def get_accident(accident_id: str):
    accident = await db.accidents.find_one({"id": accident_id}, {"_id": 0})
    if not accident:
        raise HTTPException(status_code=404, detail="Accident not found")
    if isinstance(accident.get('timestamp'), str):
        accident['timestamp'] = datetime.fromisoformat(accident['timestamp'])
    return Accident(**accident)

@api_router.patch("/accidents/{accident_id}", response_model=Accident)
async def update_accident(accident_id: str, update_data: AccidentUpdate):
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    result = await db.accidents.update_one(
        {"id": accident_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Accident not found")
    
    accident = await db.accidents.find_one({"id": accident_id}, {"_id": 0})
    if isinstance(accident.get('timestamp'), str):
        accident['timestamp'] = datetime.fromisoformat(accident['timestamp'])
    return Accident(**accident)

@api_router.get("/analytics/stats")
async def get_analytics_stats():
    total_accidents = await db.accidents.count_documents({})
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    
    today_accidents = await db.accidents.count_documents({
        "timestamp": {"$gte": today_start.isoformat()}
    })
    
    week_accidents = await db.accidents.count_documents({
        "timestamp": {"$gte": week_start.isoformat()}
    })
    
    severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    accidents = await db.accidents.find({}, {"_id": 0, "severity": 1}).to_list(1000)
    for acc in accidents:
        severity_counts[acc.get("severity", "low")] += 1
    
    return {
        "total_accidents": total_accidents,
        "today_accidents": today_accidents,
        "week_accidents": week_accidents,
        "severity_distribution": severity_counts,
        "active_sources": await db.video_sources.count_documents({"status": "active"})
    }

@api_router.post("/detection/upload-video")
async def upload_video_for_detection(file: UploadFile = File(...)):
    if not file.filename.endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(status_code=400, detail="Invalid video format")
    
    video_id = str(uuid.uuid4())
    file_path = VIDEO_STORAGE_DIR / f"upload_{video_id}.mp4"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    logging.info(f"Video uploaded: {file_path}")
    return {"video_id": video_id, "file_path": str(file_path), "message": "Video uploaded successfully"}

@api_router.post("/youtube/extract")
async def extract_youtube_url(youtube_url: str):
    """Extract direct stream URL from YouTube video"""
    stream_url, http_headers = extract_youtube_stream(youtube_url)
    return {"stream_url": stream_url, "http_headers": http_headers, "message": "YouTube stream URL extracted successfully"}

async def process_video_stream(source_id: str, video_path: str):
    try:
        if not yolo_model:
            logging.error("YOLOv8 model not loaded")
            return
        
        logging.info(f"Starting video stream processing for source {source_id} with path: {video_path[:100] if isinstance(video_path, str) else video_path}...")
        
        # Handle different video path types
        if video_path == "0" or video_path == 0:
            video_path = 0  # Webcam
        
        # For YouTube/HTTP sources, OpenCV often fails to open HTTPS streams on Windows.
        # Prefer an ffmpeg pipe when dealing with YouTube.
        use_ffmpeg_pipe = False
        source_doc = None
        if isinstance(video_path, str) and (video_path.startswith("http://") or video_path.startswith("https://")):
            source_doc = await db.video_sources.find_one({"id": source_id}, {"_id": 0})
            if source_doc and source_doc.get("type") == "youtube":
                use_ffmpeg_pipe = True
        
        # Use WARNING so it shows up even if log level isn't configured to INFO.
        logging.warning(
            f"Source {source_id} open mode: "
            f"{'ffmpeg' if use_ffmpeg_pipe else 'opencv'} "
            f"(db_type={(source_doc.get('type') if isinstance(source_doc, dict) else None)}, "
            f"path_type={'http' if isinstance(video_path, str) and (video_path.startswith('http://') or video_path.startswith('https://')) else 'non-http'})"
        )
        
        cap = None if use_ffmpeg_pipe else cv2.VideoCapture(video_path)
        
        if not use_ffmpeg_pipe:
            if not cap or not cap.isOpened():
                logging.error(f"Failed to open video stream: {video_path}")
                await db.video_sources.update_one({"id": source_id}, {"$set": {"status": "error"}})
                return

        frame_count = 0
        accident_detected = False
        accident_cooldown = 0
        last_detections: List[dict] = []

        # Tuning knobs (pixel units, seconds)
        # Run detection more often (higher temporal resolution)
        DETECTION_EVERY_N_FRAMES = 2
        # Recommended defaults (can override via env)
        COLLISION_IOU_THRESHOLD = float(os.environ.get("COLLISION_IOU_THRESHOLD", "0.4"))  # IoU > 0.4
        SPEED_DROP_MIN_FRACTION = float(os.environ.get("SPEED_DROP_MIN_FRACTION", "0.5"))  # 40-60% drop -> default 50%
        SPEED_DROP_WINDOW_SECONDS = float(os.environ.get("SPEED_DROP_WINDOW_SECONDS", "1.0"))
        DIRECTION_CHANGE_DEG = float(os.environ.get("DIRECTION_CHANGE_DEG", "50.0"))
        ASPECT_RATIO_CHANGE_FRACTION = float(os.environ.get("ASPECT_RATIO_CHANGE_FRACTION", "0.3"))  # > 30%
        VEHICLE_STOP_TIME_SECONDS = float(os.environ.get("VEHICLE_STOP_TIME_SECONDS", "3.5"))  # 3-5s
        STATIONARY_SPEED_PX_PER_S = float(os.environ.get("STATIONARY_SPEED_PX_PER_S", "25.0"))
        FRAME_CONFIRMATION_COUNT = int(os.environ.get("FRAME_CONFIRMATION_COUNT", "10"))  # 8-12 frames
        ENABLE_PEDESTRIAN_ACCIDENTS = os.environ.get("ENABLE_PEDESTRIAN_ACCIDENTS", "false").lower() == "true"

        # Lightweight tracking state (detection frames only)
        next_track_id = 1
        tracks = {}  # id -> dict
        pending_accident = None  # {"count": int, "best": dict}

        source = await db.video_sources.find_one({"id": source_id})
        if not source:
            logging.error(f"Video source {source_id} not found")
            if cap:
                cap.release()
            return

        await db.video_sources.update_one({"id": source_id}, {"$set": {"status": "active"}})
        logging.info(f"Video source {source_id} set to active")

        def _ffmpeg_mjpeg_reader(stream_url: str, headers: Optional[dict] = None):
            # Emits raw JPEG byte chunks from ffmpeg stdout
            # -re helps throttle to realtime; fps filter reduces CPU if needed
            header_lines = ""
            if headers:
                # ffmpeg expects CRLF-separated header lines ending with CRLF
                # Example: "User-Agent: ...\r\nReferer: ...\r\n"
                header_lines = "".join([f"{k}: {v}\r\n" for k, v in headers.items() if v is not None])
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-protocol_whitelist",
                "file,http,https,tcp,tls,crypto",
                "-rw_timeout",
                "15000000",
                "-user_agent",
                (headers.get("User-Agent") if headers and headers.get("User-Agent") else "Mozilla/5.0"),
                "-referer",
                (headers.get("Referer") if headers and headers.get("Referer") else "https://www.youtube.com/"),
                "-headers",
                header_lines,
                "-re",
                "-i",
                stream_url,
                "-an",
                "-vf",
                "fps=25",
                "-f",
                "image2pipe",
                "-vcodec",
                "mjpeg",
                "pipe:1",
            ]
            # Use buffered pipes so .peek() is available (avoid blocking reads)
            return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1024 * 1024)

        ffmpeg_state = {
            "proc": None,
            "buf": b"",
            "latest_frame": None,
            "latest_ts": 0.0,
            "last_err_ts": 0.0,
            "stderr_tail": "",
        }
        ffmpeg_lock = threading.Lock()
        ffmpeg_stop = threading.Event()

        def _ffmpeg_thread():
            # Blocking reader thread that won't freeze the asyncio loop.
            while not ffmpeg_stop.is_set():
                if ffmpeg_state["proc"] is None or ffmpeg_state["proc"].poll() is not None:
                    try:
                        # Use headers saved with the source (important for YouTube HLS segment fetches)
                        ffmpeg_state["proc"] = _ffmpeg_mjpeg_reader(video_path, headers=(source.get("stream_headers") if isinstance(source, dict) else None))
                        ffmpeg_state["buf"] = b""
                        logging.info(f"ffmpeg started for source {source_id}")
                    except Exception as e:
                        logging.error(f"ffmpeg failed to start for source {source_id}: {e}")
                        time.sleep(1)
                        continue

                    # Drain stderr continuously so failures are visible even if ffmpeg doesn't exit.
                    def _drain_stderr(proc):
                        try:
                            if not proc.stderr:
                                return
                            while proc.poll() is None and not ffmpeg_stop.is_set():
                                line = proc.stderr.readline()
                                if not line:
                                    break
                                text = line.decode(errors="ignore").strip()
                                if not text:
                                    continue
                                with ffmpeg_lock:
                                    tail = ffmpeg_state.get("stderr_tail", "")
                                    ffmpeg_state["stderr_tail"] = (tail + "\n" + text)[-4000:]
                                logging.error(f"ffmpeg stderr ({source_id}): {text[:500]}")
                        except Exception:
                            return

                    threading.Thread(target=_drain_stderr, args=(ffmpeg_state["proc"],), daemon=True).start()

                proc = ffmpeg_state["proc"]
                if not proc or not proc.stdout:
                    time.sleep(0.05)
                    continue

                chunk = proc.stdout.read(4096)
                if not chunk:
                    # If ffmpeg exited, log stderr once
                    if proc.poll() is not None and proc.stderr:
                        try:
                            err = proc.stderr.read().decode(errors="ignore")
                            if err:
                                logging.error(f"ffmpeg stderr ({source_id}): {err[:2000]}")
                        except Exception:
                            pass
                        ffmpeg_state["proc"] = None
                    time.sleep(0.05)
                    continue

                ffmpeg_state["buf"] += chunk

                # Extract one JPEG frame (start: FFD8, end: FFD9)
                buf = ffmpeg_state["buf"]
                soi = buf.find(b"\xff\xd8")
                eoi = buf.find(b"\xff\xd9", soi + 2) if soi != -1 else -1
                if soi == -1 or eoi == -1:
                    if len(buf) > 5_000_000:
                        ffmpeg_state["buf"] = buf[-1_000_000:]
                    continue

                jpg = buf[soi : eoi + 2]
                ffmpeg_state["buf"] = buf[eoi + 2 :]
                arr = np.frombuffer(jpg, dtype=np.uint8)
                fr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if fr is None:
                    continue

                with ffmpeg_lock:
                    ffmpeg_state["latest_frame"] = fr
                    ffmpeg_state["latest_ts"] = time.time()

        ffmpeg_thread = None
        if use_ffmpeg_pipe:
            logging.warning(f"Starting ffmpeg reader thread for source {source_id}")
            ffmpeg_thread = threading.Thread(target=_ffmpeg_thread, daemon=True)
            ffmpeg_thread.start()

        while source_id in active_streams and (use_ffmpeg_pipe or cap.isOpened()):
            if use_ffmpeg_pipe:
                with ffmpeg_lock:
                    frame = ffmpeg_state["latest_frame"]
                    last_ts = ffmpeg_state["latest_ts"]
                ret = frame is not None

                # If no frames for a while, mark error so UI can show status
                if not ret and (time.time() - last_ts) > 10:
                    await db.video_sources.update_one({"id": source_id}, {"$set": {"status": "error"}})
            else:
                ret, frame = cap.read()

            if not ret:
                logging.warning(f"Failed to read frame from source {source_id}, restarting...")
                if use_ffmpeg_pipe:
                    await asyncio.sleep(1)
                    continue
                else:
                    cap.release()
                    await asyncio.sleep(2)
                    cap = cv2.VideoCapture(video_path)
                    if not cap.isOpened():
                        break
                    continue
            frame_count += 1

            # Process every 2nd frame for detection to save compute,
            # but send all frames for display at higher FPS
            process_detection = (frame_count % DETECTION_EVERY_N_FRAMES == 0)

            try:
                detections = []
                # Default values so they are always defined even if we skip detection logic
                is_collision = False
                accident_type_str = ""
                severity_level = "medium"

                if process_detection:
                    results = yolo_model(frame, conf=0.25, verbose=False)

                    for result in results:
                        boxes = result.boxes
                        for box in boxes:
                            cls_id = int(box.cls[0])
                            conf = float(box.conf[0])
                            class_name = result.names[cls_id]

                            if class_name in ['car', 'truck', 'bus', 'motorcycle', 'person'] and conf > 0.4:
                                detections.append({
                                    "class": class_name,
                                    "confidence": conf,
                                    "bbox": box.xyxy[0].tolist()
                                })
                    # Cache detections so UI boxes don't flicker on non-detection frames
                    last_detections = detections
                else:
                    # Use last known detections between YOLO runs for stable rendering
                    detections = last_detections

                # Accident detection logic
                # Only evaluate on detection frames (to avoid reusing stale boxes)
                if process_detection and len(detections) >= 2 and accident_cooldown == 0:
                    vehicles = [d for d in detections if d['class'] in ['car', 'truck', 'bus', 'motorcycle']]
                    persons = [d for d in detections if d['class'] == 'person']

                    # Check for collision indicators based on actual bounding box contact/overlap:
                    # 1. Two vehicle boxes touching/overlapping (vehicle collision)
                    # 2. Person box intersecting a vehicle box (pedestrian accident)
                    if len(vehicles) >= 2:
                        now_ts = datetime.now(timezone.utc).timestamp()

                        def bbox_center(b):
                            return ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)

                        def bbox_aspect_ratio(b):
                            w = max(1.0, (b[2] - b[0]))
                            h = max(1.0, (b[3] - b[1]))
                            return w / h

                        def iou(b1, b2):
                            x1 = max(b1[0], b2[0])
                            y1 = max(b1[1], b2[1])
                            x2 = min(b1[2], b2[2])
                            y2 = min(b1[3], b2[3])
                            inter_w = max(0.0, x2 - x1)
                            inter_h = max(0.0, y2 - y1)
                            inter_area = inter_w * inter_h
                            if inter_area <= 0:
                                return 0.0
                            a1 = max(1.0, (b1[2] - b1[0]) * (b1[3] - b1[1]))
                            a2 = max(1.0, (b2[2] - b2[0]) * (b2[3] - b2[1]))
                            return inter_area / (a1 + a2 - inter_area)

                        # --- Update tracks via nearest-neighbor association ---
                        # Associate detections to existing tracks by center distance.
                        active_ids = list(tracks.keys())
                        used_tracks = set()
                        det_to_track = {}

                        # Greedy matching (good enough for small counts)
                        for det_idx, det in enumerate(vehicles):
                            c = bbox_center(det["bbox"])
                            best_id = None
                            best_dist = None
                            for tid in active_ids:
                                if tid in used_tracks:
                                    continue
                                tc = tracks[tid]["center"]
                                dist = ((c[0] - tc[0]) ** 2 + (c[1] - tc[1]) ** 2) ** 0.5
                                if best_dist is None or dist < best_dist:
                                    best_dist = dist
                                    best_id = tid
                            # Gate: avoid matching across the scene
                            if best_id is not None and best_dist is not None and best_dist < 120:
                                det_to_track[det_idx] = best_id
                                used_tracks.add(best_id)

                        # Create new tracks for unmatched detections
                        for det_idx, det in enumerate(vehicles):
                            if det_idx in det_to_track:
                                continue
                            tid = next_track_id
                            next_track_id += 1
                            c = bbox_center(det["bbox"])
                            ar = bbox_aspect_ratio(det["bbox"])
                            tracks[tid] = {
                                "id": tid,
                                "center": c,
                                "bbox": det["bbox"],
                                "aspect_ratio_base": ar,
                                "aspect_ratio_last": ar,
                                "last_ts": now_ts,
                                "vel": (0.0, 0.0),
                                "speed": 0.0,
                                "speed_hist": [],  # list of (ts, speed)
                                "vel_hist": [],  # list of (ts, (vx, vy))
                                "stationary_since": None,
                                "collided_ts": None,
                            }
                            det_to_track[det_idx] = tid

                        # Update matched tracks
                        for det_idx, tid in det_to_track.items():
                            det = vehicles[det_idx]
                            tr = tracks[tid]
                            prev_c = tr["center"]
                            prev_ts = tr["last_ts"]
                            dt = max(1e-3, now_ts - prev_ts)
                            c = bbox_center(det["bbox"])
                            vx = (c[0] - prev_c[0]) / dt
                            vy = (c[1] - prev_c[1]) / dt
                            sp = (vx * vx + vy * vy) ** 0.5

                            tr["center"] = c
                            tr["bbox"] = det["bbox"]
                            tr["last_ts"] = now_ts
                            tr["vel"] = (vx, vy)
                            tr["speed"] = sp
                            ar = bbox_aspect_ratio(det["bbox"])
                            tr["aspect_ratio_last"] = ar

                            tr["speed_hist"].append((now_ts, sp))
                            tr["vel_hist"].append((now_ts, (vx, vy)))
                            # Keep ~2 seconds history
                            tr["speed_hist"] = [(t, s) for (t, s) in tr["speed_hist"] if now_ts - t <= 2.0]
                            tr["vel_hist"] = [(t, v) for (t, v) in tr["vel_hist"] if now_ts - t <= 2.0]

                            if sp <= STATIONARY_SPEED_PX_PER_S:
                                if tr["stationary_since"] is None:
                                    tr["stationary_since"] = now_ts
                            else:
                                tr["stationary_since"] = None

                        # Prune stale tracks
                        stale_ids = [tid for tid, tr in tracks.items() if (now_ts - tr["last_ts"]) > 2.0]
                        for tid in stale_ids:
                            del tracks[tid]

                        # --- Compute best IoU pair (collision candidate) ---
                        best_pair = None  # (iou, tid1, tid2)
                        track_ids = list(set(det_to_track.values()))
                        for i, tid1 in enumerate(track_ids):
                            for tid2 in track_ids[i + 1:]:
                                b1 = tracks[tid1]["bbox"]
                                b2 = tracks[tid2]["bbox"]
                                val = iou(b1, b2)
                                if best_pair is None or val > best_pair[0]:
                                    best_pair = (val, tid1, tid2)

                        # Helper to compute average speed in a window ending SPEED_DROP_WINDOW_SECONDS ago
                        def avg_speed_before(tr):
                            cutoff = now_ts - SPEED_DROP_WINDOW_SECONDS
                            older = [s for (t, s) in tr["speed_hist"] if t <= cutoff]
                            if not older:
                                return None
                            return sum(older) / len(older)

                        # New accident rule:
                        # - Two vehicles' boxes overlap above COLLISION_IOU_THRESHOLD
                        # - AND at least one of the two has a sudden speed drop
                        if best_pair and best_pair[0] >= COLLISION_IOU_THRESHOLD:
                            _, tid1, tid2 = best_pair
                            tr1 = tracks.get(tid1)
                            tr2 = tracks.get(tid2)
                            sudden_drop = False

                            for tr in (tr1, tr2):
                                if not tr:
                                    continue
                                prev_avg = avg_speed_before(tr)
                                if prev_avg is not None and prev_avg > 1e-3:
                                    if tr["speed"] <= (1.0 - SPEED_DROP_MIN_FRACTION) * prev_avg:
                                        sudden_drop = True
                                        break

                            if sudden_drop:
                                is_collision = True
                                accident_type_str = "Vehicle collision detected - overlap + sudden deceleration"
                                severity_level = "high"
                
                # Optional pedestrian accident detection (disabled by default to avoid false positives)
                if ENABLE_PEDESTRIAN_ACCIDENTS and not is_collision and len(persons) > 0 and len(vehicles) > 0:
                    # Check for person-vehicle intersection (pedestrian accident)
                    for person in persons:
                        for vehicle in vehicles:
                            p_bbox = person['bbox']
                            v_bbox = vehicle['bbox']
                            
                            # Compute box intersection directly
                            x1 = max(p_bbox[0], v_bbox[0])
                            y1 = max(p_bbox[1], v_bbox[1])
                            x2 = min(p_bbox[2], v_bbox[2])
                            y2 = min(p_bbox[3], v_bbox[3])

                            inter_w = max(0, x2 - x1)
                            inter_h = max(0, y2 - y1)
                            inter_area = inter_w * inter_h

                            if inter_area > 0:
                                is_collision = True
                                accident_type_str = "Pedestrian accident - person and vehicle boxes intersecting"
                                severity_level = "critical"
                                break
                        if is_collision:
                            break
                
                if is_collision:
                    accident_cooldown = 100  # Cooldown for 100 frames (~30 seconds)
                    
                    snapshot_path = VIDEO_STORAGE_DIR / f"accident_{uuid.uuid4()}.jpg"
                    cv2.imwrite(str(snapshot_path), frame)
                    
                    accident = Accident(
                        location=source.get("location", "Unknown"),
                        severity=severity_level,
                        accident_type=accident_type_str,
                        snapshot_path=str(snapshot_path),
                        source_id=source_id,
                        source_name=source.get("name", "Unknown"),
                        confidence=max([d["confidence"] for d in detections]),
                        details=f"Detected {len(vehicles)} vehicles and {len(persons)} persons in close proximity"
                    )
                    
                    accident_dict = accident.model_dump()
                    accident_dict["timestamp"] = accident_dict["timestamp"].isoformat()
                    await db.accidents.insert_one(accident_dict)
                    
                    # Send alerts
                    send_email_alert(accident)
                    send_sms_alert(accident)
                    
                    await manager.broadcast({
                        "type": "accident_detected",
                        "accident": json.loads(accident.model_dump_json())
                    })
                    
                    logging.info(f"🚨 Accident detected at {accident.location} - Severity: {accident.severity}")
            
                if accident_cooldown > 0:
                    accident_cooldown -= 1
                
                # Encode frame to base64 for WebSocket transmission
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                await manager.broadcast({
                    "type": "detection_frame",
                    "source_id": source_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "detections": detections,
                    "frame": frame_base64
                })
            
            except Exception as e:
                logging.error(f"Detection error: {e}")

            # Smaller sleep for higher frame rate to clients (~40–50 FPS depending on source)
            await asyncio.sleep(0.02)

        if cap:
            cap.release()
        if use_ffmpeg_pipe:
            ffmpeg_stop.set()
            # best-effort terminate underlying ffmpeg process
            proc = ffmpeg_state.get("proc")
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
        await db.video_sources.update_one({"id": source_id}, {"$set": {"status": "inactive"}})
        if source_id in active_streams:
            del active_streams[source_id]
        logging.info(f"Video source {source_id} stopped")
    except Exception as e:
        logging.error(f"process_video_stream crashed for source {source_id}: {e}")
        try:
            await db.video_sources.update_one({"id": source_id}, {"$set": {"status": "error"}})
        except Exception:
            pass

@api_router.post("/detection/start/{source_id}")
async def start_detection(source_id: str):
    source = await db.video_sources.find_one({"id": source_id})
    if not source:
        raise HTTPException(status_code=404, detail="Video source not found")
    
    if source_id in active_streams:
        raise HTTPException(status_code=400, detail="Detection already running for this source")
    
    if source["type"] == "webcam":
        video_path = 0
    elif source["type"] == "youtube":
        # Prefer stored derived stream URL; otherwise re-extract at start (stream URLs can expire)
        if source.get("stream_url"):
            video_path = source["stream_url"]
        else:
            url = source.get("url")
            if not url:
                raise HTTPException(status_code=400, detail="YouTube URL not configured")
            video_path, http_headers = extract_youtube_stream(url)
            await db.video_sources.update_one({"id": source_id}, {"$set": {"stream_url": video_path, "stream_headers": http_headers}})
        # Ensure headers exist (some streams need them for HLS segments)
        if not source.get("stream_headers") and source.get("url"):
            try:
                _, http_headers = extract_youtube_stream(source["url"])
                await db.video_sources.update_one({"id": source_id}, {"$set": {"stream_headers": http_headers}})
                source["stream_headers"] = http_headers
            except Exception:
                pass
    elif source["type"] == "rtsp":
        video_path = source["url"]
    elif source["type"] == "file":
        video_path = source["url"]
    else:
        raise HTTPException(status_code=400, detail="Invalid source type")
    
    task = asyncio.create_task(process_video_stream(source_id, video_path))
    active_streams[source_id] = task
    
    logging.info(f"Detection started for source {source_id}")
    return {"message": "Detection started", "source_id": source_id}

@api_router.post("/detection/stop/{source_id}")
async def stop_detection(source_id: str):
    if source_id not in active_streams:
        raise HTTPException(status_code=400, detail="No active detection for this source")
    
    try:
        active_streams[source_id].cancel()
    except:
        pass
    
    del active_streams[source_id]
    
    await db.video_sources.update_one({"id": source_id}, {"$set": {"status": "inactive"}})
    
    logging.info(f"Detection stopped for source {source_id}")
    return {"message": "Detection stopped", "source_id": source_id}

@api_router.websocket("/ws/detection")
async def websocket_detection(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"status": "connected"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@api_router.get("/")
async def root():
    return {"message": "Accident Detection System API"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()