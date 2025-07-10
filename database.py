from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user_credentials(user_id: str):
    """Get user credentials from Supabase database."""
    response = supabase.table("user_ga_connections").select("refresh_token, property_id").eq("user_id", user_id).execute()
    if response.data:
        # Filter for rows with a non-null property_id
        valid_rows = [row for row in response.data if row["property_id"]]
        if not valid_rows:
            raise Exception(f"No property_id found for user {user_id}")
        first = valid_rows[0]
        return first["refresh_token"], first["property_id"]
    else:
        raise Exception(f"User {user_id} not found in Supabase.")