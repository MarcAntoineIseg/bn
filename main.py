from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from services.supabase_client import get_user_tokens
from services.token_manager import check_and_refresh_token
import datetime
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/fetch-ga-sessions")
async def fetch_ga_sessions(request: Request):
    payload = await request.json()

    # Extract userId from nested JSON
    try:
        body = payload["body"]
        user_id = body["userId"]
        ga_property_id = body["googleAnalyticsData"]["selectedProperty"]["id"]
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing field in request: {e}")

    # get tokens from supabase
    tokens = get_user_tokens(user_id)
    if not tokens:
        raise HTTPException(status_code=404, detail="User not found in Supabase")

    # check / refresh
    updated_tokens = await check_and_refresh_token(user_id, tokens)
    ga_access_token = updated_tokens["access_token"]

    # query GA4
    today = datetime.datetime.utcnow()
    thirty_days_ago = today - datetime.timedelta(days=30)

    report_body = {
        "dimensions": [{"name": "date"}],
        "metrics": [{"name": "sessions"}],
        "dateRanges": [
            {
                "startDate": thirty_days_ago.strftime("%Y-%m-%d"),
                "endDate": today.strftime("%Y-%m-%d")
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        ga_response = await client.post(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{ga_property_id}:runReport",
            json=report_body,
            headers={"Authorization": f"Bearer {ga_access_token}"}
        )
        ga_data = ga_response.json()

    # transform to simpler JSON
    transformed = []
    for row in ga_data.get("rows", []):
        date_str = row["dimensionValues"][0]["value"]
        date_fmt = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        sessions = int(row["metricValues"][0]["value"])
        transformed.append({
            "date": date_fmt,
            "sessions": sessions
        })

    return transformed

