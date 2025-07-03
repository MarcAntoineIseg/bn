from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user_tokens(user_id: str):
    """Fetch access/refresh tokens for a user"""
    response = supabase.table("user_ga_connections").select("*").eq("user_id", user_id).execute()
    if response.data:
        return response.data[0]
    return None
    
def update_user_tokens(user_id: str, new_access_token: str, new_expiry: str):
    supabase.table("user_tokens").update({
        "access_token": new_access_token,
        "token_expires_at": new_expiry
    }).eq("userId", user_id).execute()

