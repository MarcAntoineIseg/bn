import os
from dotenv import load_dotenv

load_dotenv()

# Environment variables with validation
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validation
if not GOOGLE_CLIENT_ID or GOOGLE_CLIENT_ID == "YOUR_GOOGLE_CLIENT_ID":
    raise ValueError("GOOGLE_CLIENT_ID environment variable is not set or is using placeholder value")
if not GOOGLE_CLIENT_SECRET or GOOGLE_CLIENT_SECRET == "YOUR_GOOGLE_CLIENT_SECRET":
    raise ValueError("GOOGLE_CLIENT_SECRET environment variable is not set or is using placeholder value")
if not SUPABASE_URL or SUPABASE_URL == "YOUR_SUPABASE_URL":
    raise ValueError("SUPABASE_URL environment variable is not set or is using placeholder value")
if not SUPABASE_KEY or SUPABASE_KEY == "YOUR_SUPABASE_SERVICE_ROLE_KEY":
    raise ValueError("SUPABASE_KEY environment variable is not set or is using placeholder value")