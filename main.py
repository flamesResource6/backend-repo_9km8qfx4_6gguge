import os
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import db, create_document, get_documents
from schemas import TrafficEvent

app = FastAPI(title="Traffic Tracker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Traffic Tracker API is running"}

@app.get("/test")
def test_database():
    """Test endpoint to check database connectivity"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, 'name', None) or "Unknown"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# Models for API
class TrackEventIn(BaseModel):
    path: str
    event: str = "view"
    source: Optional[str] = None

class TrackEventOut(BaseModel):
    id: str

@app.post("/api/track", response_model=TrackEventOut)
async def track_event(payload: TrackEventIn, request: Request):
    """Capture a traffic event with metadata"""
    try:
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
        ua = request.headers.get("user-agent")
        evt = TrafficEvent(
            path=payload.path,
            source=payload.source,
            event=payload.event,
            user_agent=ua,
            ip=ip,
        )
        inserted_id = create_document("trafficevent", evt)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats(path: Optional[str] = None, event: Optional[str] = None, limit: int = 50):
    """Get recent events, optionally filtered"""
    try:
        filt = {}
        if path:
            filt["path"] = path
        if event:
            filt["event"] = event
        docs = get_documents("trafficevent", filt, limit)
        # Normalize for JSON serialization
        out = []
        for d in docs:
            d["_id"] = str(d.get("_id"))
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])  # string format
            if d.get("updated_at"):
                d["updated_at"] = str(d["updated_at"])  # string format
            out.append(d)
        return {"items": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
