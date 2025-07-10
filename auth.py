import requests
from google.oauth2.credentials import Credentials
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

def always_refresh_user_tokens(refresh_token: str) -> Credentials:
    """Always refresh Google OAuth tokens to ensure they're valid."""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    try:
        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            error_details = response.text
            try:
                error_json = response.json()
                error_msg = f"HTTP {response.status_code}: {error_json.get('error', 'Unknown error')}"
                if 'error_description' in error_json:
                    error_msg += f" - {error_json['error_description']}"
            except:
                error_msg = f"HTTP {response.status_code}: {error_details}"
            raise Exception(f"Failed to refresh token: {error_msg}")
        tokens = response.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise Exception("No access token received from Google")
        new_refresh_token = tokens.get("refresh_token", refresh_token)
        creds = Credentials(
            token=access_token,
            refresh_token=new_refresh_token,
            token_uri=token_url,
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        return creds
    except requests.RequestException as e:
        raise Exception(f"Network error while refreshing token: {str(e)}")