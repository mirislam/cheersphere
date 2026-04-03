import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, Depends, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime
import json
import shutil
import uuid
from typing import Dict, List

from app.db import init_db, get_db, Event, Message
from app.services.pdf_service import generate_event_pdf

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    pass

app = FastAPI(lifespan=lifespan)
import random

# Themes definition
THEMES = [
    "General",
    "Farewell",
    "Birthday",
    "Good Job",
    "Promotion",
    "Work Anniversary"
]

def get_random_banner(theme: str) -> str:
    """Select 1 of 20 randomly downloaded local images for the theme"""
    if theme not in THEMES:
        theme = "General"
    image_id = random.randint(1, 20)
    return f"/static/themes/{theme}/{image_id}.jpg"

# Setup Templates and Static
import zoneinfo
from datetime import timezone

def to_pdt(dt):
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    pdt_tz = zoneinfo.ZoneInfo("America/Los_Angeles")
    # strftime to match exact format: Mar 31, 2026 08:30 PM
    return dt.astimezone(pdt_tz).strftime('%b %d, %Y %I:%M %p')

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)
templates.env.filters['pdt'] = to_pdt

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
if not os.path.exists(os.path.join(static_dir, "images")):
    os.makedirs(os.path.join(static_dir, "images"))
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Connection manager for websockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, event_id: int):
        await websocket.accept()
        if event_id not in self.active_connections:
            self.active_connections[event_id] = []
        self.active_connections[event_id].append(websocket)

    def disconnect(self, websocket: WebSocket, event_id: int):
        if event_id in self.active_connections:
            self.active_connections[event_id].remove(websocket)

    async def broadcast(self, message: dict, event_id: int):
        if event_id in self.active_connections:
            text_data = json.dumps(message)
            for connection in self.active_connections[event_id]:
                await connection.send_text(text_data)

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.created_at.desc()).all()
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request, "events": events})

@app.get("/dash", response_class=HTMLResponse)
async def admin_dash(request: Request, db: Session = Depends(get_db)):
    events = db.query(Event).order_by(Event.created_at.desc()).all()
    return templates.TemplateResponse(request=request, name="dash.html", context={"request": request, "events": events})

@app.post("/api/event/{event_id}/delete")
async def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if event:
        if event.image_path:
            # Reconstruct absolute filepath
            filepath = os.path.join(static_dir, event.image_path.replace("/static/", ""))
            if os.path.exists(filepath) and os.path.isfile(filepath):
                try:
                    os.unlink(filepath)
                except Exception:
                    pass
        # SQLite cascades doesn't trigger gracefully all the time in basic config
        db.query(Message).filter(Message.event_id == event_id).delete()
        db.delete(event)
        db.commit()
    return RedirectResponse(url="/dash", status_code=303)

@app.post("/api/reset-db")
async def reset_db(db: Session = Depends(get_db)):
    db.query(Message).delete()
    db.query(Event).delete()
    db.commit()
    
    # Clean up uploaded images
    images_dir = os.path.join(static_dir, "images")
    if os.path.exists(images_dir):
        for filename in os.listdir(images_dir):
            file_path = os.path.join(images_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception:
                pass
                
    return RedirectResponse(url="/dash", status_code=303)

@app.post("/events", response_class=HTMLResponse)
async def create_event(
    request: Request, 
    title: str = Form(...), 
    description: str = Form(""), 
    theme: str = Form("General"),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    image_path = None
    if image and image.filename:
        # Generate unique filename
        ext = os.path.splitext(image.filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        image_relative_path = os.path.join("images", unique_filename)
        file_path = os.path.join(static_dir, image_relative_path)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
            
        image_path = f"/static/{image_relative_path}"

    banner_url = get_random_banner(theme)

    new_event = Event(
        title=title, 
        description=description, 
        theme=theme, 
        banner_url=banner_url, 
        image_path=image_path
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return RedirectResponse(url="/", status_code=303)

@app.get("/event/{event_id}", response_class=HTMLResponse)
async def read_event(request: Request, event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return HTMLResponse("Event not found", status_code=404)
    # Get messages ordered by newest first
    messages = db.query(Message).filter(Message.event_id == event_id).order_by(Message.created_at.desc()).all()
    return templates.TemplateResponse(request=request, name="event.html", context={"request": request, "event": event, "messages": messages})

@app.websocket("/ws/event/{event_id}")
async def websocket_endpoint(websocket: WebSocket, event_id: int, db: Session = Depends(get_db)):
    await manager.connect(websocket, event_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Sanity checks and length limits
            author = message_data.get("author", "").strip()[:50]
            content = message_data.get("content", "").strip()[:250]
            
            if not author or not content:
                continue
            
            # Save to database
            new_message = Message(
                event_id=event_id,
                author=author,
                content=content
            )
            db.add(new_message)
            db.commit()
            db.refresh(new_message)
            
            # Broadcast to clients
            broadcast_data = {
                "id": new_message.id,
                "author": new_message.author,
                "content": new_message.content,
                "created_at": new_message.created_at.isoformat()
            }
            await manager.broadcast(broadcast_data, event_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, event_id)

@app.get("/event/{event_id}/export")
async def export_pdf(request: Request, event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return HTMLResponse("Event not found", status_code=404)
        
    messages = db.query(Message).filter(Message.event_id == event_id).order_by(Message.created_at.asc()).all()
    
    pdf_buffer = generate_event_pdf(request, event, messages)
    
    filename = f"event-{event_id}-export.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
