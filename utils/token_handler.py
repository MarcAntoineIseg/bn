import os
import httpx
import datetime
from dotenv import load_dotenv
from services.supabase_client import update_user_tokens

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")


async def refresh_access_token(refresh_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
        )

    if response.status_code == 200:
        new_data = response.json()
        return {
            "access_token": new_data["access_token"],
            "expires_in": new_data["expires_in"]
        }
    else:
        raise Exception("Failed to refresh token: " + response.text)


async def check_and_refresh_token(user_id: str, tokens: dict):
    expiry = datetime.datetime.fromisoformat(tokens["token_expires_at"].replace("Z", "+00:00"))
    now = datetime.datetime.now(datetime.timezone.utc)

    if expiry < now:
        print("Token expired. Refreshing...")
        new_token_data = await refresh_access_token(tokens["refresh_token"])
        
        # Calculate new expiry
        new_expiry = (now + datetime.timedelta(seconds=new_token_data["expires_in"])).isoformat()
        
        # Update Supabase
        update_user_tokens(user_id, new_token_data["access_token"], new_expiry)

        # Return updated token set
        tokens["access_token"] = new_token_data["access_token"]
        tokens["token_expires_at"] = new_expiry
    else:
        print("Token still valid.")

    return tokens
