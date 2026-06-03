import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./travel_planner.db")
PORT = int(os.getenv("PORT", "8000"))
