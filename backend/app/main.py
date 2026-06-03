from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from sqlmodel import Session, select
import uvicorn

from app.database import init_db, get_session
from app.config import GEMINI_API_KEY, PORT
from app.models import Itinerary
from app.agents.coordinator import TravelCoordinator

app = FastAPI(title="Multi-Agent Travel Planner API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup DB initialization
@app.on_event("startup")
def on_startup():
    init_db()

class ChatRequest(BaseModel):
    message: str
    itinerary_id: Optional[int] = None

class ChatResponse(BaseModel):
    text: str
    itinerary_id: Optional[int]
    itinerary: Optional[dict]

@app.get("/health")
def health_check():
    return {"status": "ok", "gemini_configured": bool(GEMINI_API_KEY)}

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise HTTPException(
            status_code=400,
            detail="GEMINI_API_KEY is not configured in backend/.env. Please add a valid Gemini API Key."
        )
    
    try:
        coordinator = TravelCoordinator(api_key=GEMINI_API_KEY, itinerary_id=payload.itinerary_id)
        result = coordinator.execute_chat(payload.message)
        return ChatResponse(
            text=result["text"],
            itinerary_id=result["itinerary_id"],
            itinerary=result["itinerary"]
        )
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/itineraries")
def list_itineraries(session: Session = Depends(get_session)):
    statement = select(Itinerary).order_by(Itinerary.created_at.desc())
    itineraries = session.exec(statement).all()
    results = []
    for it in itineraries:
        import json
        results.append({
            "id": it.id,
            "title": it.title,
            "destination": it.destination,
            "start_date": it.start_date,
            "end_date": it.end_date,
            "created_at": it.created_at
        })
    return results

@app.get("/api/itineraries/{itinerary_id}")
def get_itinerary(itinerary_id: int, session: Session = Depends(get_session)):
    itinerary = session.get(Itinerary, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
        
    import json
    return {
        "id": itinerary.id,
        "title": itinerary.title,
        "destination": itinerary.destination,
        "start_date": itinerary.start_date,
        "end_date": itinerary.end_date,
        "timeline": json.loads(itinerary.timeline_json),
        "routes": json.loads(itinerary.routes_json)
    }

@app.delete("/api/itineraries/{itinerary_id}")
def delete_itinerary(itinerary_id: int, session: Session = Depends(get_session)):
    itinerary = session.get(Itinerary, itinerary_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    session.delete(itinerary)
    session.commit()
    return {"status": "deleted"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
