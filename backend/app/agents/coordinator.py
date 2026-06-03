import json
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from sqlmodel import select

from app.database import get_db_session
from app.models import ChatMessage, Itinerary
from app.agents.tools import (
    search_places_of_interest as tools_search_places,
    get_weather_for_destination as tools_get_weather,
    save_itinerary_plan as tools_save_itinerary
)
from app.config import GEMINI_MODEL_NAME

SYSTEM_INSTRUCTION = """
You are a highly efficient and creative Multi-Agent Travel Planner.
Your goal is to build, customize, and refine detailed travel itineraries for users.

To achieve this, you have access to three tools:
1. `search_places_of_interest(query, location)`: Use this to search for attractions, hotels, cafes, parks, etc. at the destination.
2. `get_weather_for_destination(city, date)`: Use this to check weather forecasts for the trip dates.
3. `save_itinerary_plan(title, destination, start_date, end_date, days, itinerary_id)`: You MUST call this tool whenever you create a new itinerary, edit, adjust, or swap activities in the timeline.

CRITICAL INSTRUCTIONS FOR `save_itinerary_plan` argument `days`:
- In the `days` parameter, every activity object MUST contain:
  1. "name": The exact name of the landmark, sight, or place (e.g., "India Gate", "Red Fort", "Pike Place Market"). This is REQUIRED and must NOT be empty. Do not combine the name into the description!
  2. "time": The time or period (e.g., "10:00 AM", "Morning", "Afternoon", "Evening").
  3. "description": A brief description of what to do there.
  4. "weather_condition": (Optional) e.g., "Sunny, 72F".
- You do NOT need to supply "latitude" and "longitude" in the activity objects; the backend will automatically find them for you using your "name"! But you MUST supply the "name" key.

Work Process:
1. If the user asks for a trip, first query the weather for the dates and search for interesting places.
2. Formulate a daily plan. Ensure that coordinates are realistic (retrieved via the search tool).
3. Call `save_itinerary_plan` to persist the timeline and routes.
4. Respond to the user with a friendly text response highlighting the weather, the places chosen, and verifying that the map has been updated.
5. If the user asks for adjustments (e.g. "move X to day 2", "swap Y with something indoor"), adjust the timeline and call `save_itinerary_plan` again to save the changes.
"""

class TravelCoordinator:
    def __init__(self, api_key: str, itinerary_id: Optional[int] = None):
        self.api_key = api_key
        self.itinerary_id = itinerary_id
        self.last_saved_id = itinerary_id
        
        # Configure client
        genai.configure(api_key=self.api_key)
        
    def search_places_of_interest(self, query: str, location: str) -> str:
        return tools_search_places(query, location)
        
    def get_weather_for_destination(self, city: str, date: str) -> str:
        return tools_get_weather(city, date)
        
    def save_itinerary_plan(
        self,
        title: str,
        destination: str,
        start_date: str,
        end_date: str,
        days: list[dict],
        itinerary_id: Optional[int] = None
    ) -> str:
        # Bind itinerary_id to instance context to prevent creating duplicate itineraries during adjustments
        target_id = itinerary_id or self.last_saved_id
        result = tools_save_itinerary(
            title=title,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            days=days,
            itinerary_id=target_id
        )
        try:
            data = json.loads(result)
            self.last_saved_id = data.get("id")
        except Exception as e:
            print(f"Error parsing save_itinerary_plan result: {e}")
        return result

    def execute_chat(self, user_message: str) -> Dict[str, Any]:
        """
        Executes a single conversational step, runs tool calling loops automatically,
        and saves message logs to SQLite.
        """
        # 1. Load history from database
        db_messages = []
        if self.itinerary_id:
            with get_db_session() as session:
                statement = (
                    select(ChatMessage)
                    .where(ChatMessage.itinerary_id == self.itinerary_id)
                    .order_by(ChatMessage.created_at)
                )
                db_messages = session.exec(statement).all()

        # 2. Format history for Gemini
        gemini_history = []
        for msg in db_messages:
            gemini_history.append({
                "role": "user" if msg.role == "user" else "model",
                "parts": [msg.content]
            })

        # 3. Initialize Model with tools
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL_NAME,
            tools=[
                self.search_places_of_interest,
                self.get_weather_for_destination,
                self.save_itinerary_plan
            ],
            system_instruction=SYSTEM_INSTRUCTION
        )

        # 4. Start automatic function calling chat session
        chat = model.start_chat(
            history=gemini_history,
            enable_automatic_function_calling=True
        )

        # 5. Send message and await text output
        response = chat.send_message(user_message)
        text_response = response.text

        # 6. Save messages to SQLite
        with get_db_session() as session:
            # If we don't have itinerary_id yet but one was created in this session, use it
            current_itinerary_id = self.last_saved_id
            
            # Save user message
            user_chat = ChatMessage(
                itinerary_id=current_itinerary_id,
                role="user",
                content=user_message
            )
            session.add(user_chat)
            
            # Save model response
            model_chat = ChatMessage(
                itinerary_id=current_itinerary_id,
                role="model",
                content=text_response
            )
            session.add(model_chat)
            session.commit()

        # 7. Load latest itinerary details if saved
        itinerary_data = None
        if self.last_saved_id:
            with get_db_session() as session:
                itinerary_obj = session.get(Itinerary, self.last_saved_id)
                if itinerary_obj:
                    itinerary_data = {
                        "id": itinerary_obj.id,
                        "title": itinerary_obj.title,
                        "destination": itinerary_obj.destination,
                        "start_date": itinerary_obj.start_date,
                        "end_date": itinerary_obj.end_date,
                        "timeline": json.loads(itinerary_obj.timeline_json),
                        "routes": json.loads(itinerary_obj.routes_json)
                    }

        return {
            "text": text_response,
            "itinerary_id": self.last_saved_id,
            "itinerary": itinerary_data
        }
