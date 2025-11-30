import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# Default to gemini-1.5-flash if not specified, but allow override from env
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

# Database paths
DB_PATH = "lakehouse.db"
