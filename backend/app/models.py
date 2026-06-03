from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class Itinerary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    destination: str
    start_date: str
    end_date: str
    timeline_json: str  # JSON string representing array of day itineraries and activities
    routes_json: str    # JSON string representing routes / polyline geometry
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class PlacesCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    query: str = Field(index=True)
    results_json: str
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class WeatherCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    city: str = Field(index=True)
    date: str = Field(index=True)  # YYYY-MM-DD format
    weather_info_json: str
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    itinerary_id: Optional[int] = Field(default=None, index=True)
    role: str  # "user" or "model"
    content: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
