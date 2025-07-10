from datetime import datetime, timedelta

def get_date_suggestions() -> dict:
    """
    Get common date range suggestions for GA4 queries.
    
    This provides pre-calculated date ranges that are commonly used in analytics.
    Use this to help convert relative date expressions into specific dates.
    """
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    year_ago = today - timedelta(days=365)
    
    suggestions = {
        "today": {
            "start_date": today.strftime("%Y-%m-%d"),
            "end_date": today.strftime("%Y-%m-%d")
        },
        "yesterday": {
            "start_date": yesterday.strftime("%Y-%m-%d"),
            "end_date": yesterday.strftime("%Y-%m-%d")
        },
        "last_7_days": {
            "start_date": week_ago.strftime("%Y-%m-%d"),
            "end_date": yesterday.strftime("%Y-%m-%d")
        },
        "last_30_days": {
            "start_date": month_ago.strftime("%Y-%m-%d"),
            "end_date": yesterday.strftime("%Y-%m-%d")
        },
        "last_year": {
            "start_date": year_ago.strftime("%Y-%m-%d"),
            "end_date": yesterday.strftime("%Y-%m-%d")
        },
        "this_month": {
            "start_date": today.replace(day=1).strftime("%Y-%m-%d"),
            "end_date": today.strftime("%Y-%m-%d")
        },
        "last_month": {
            "start_date": (today.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d"),
            "end_date": (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
        }
    }
    
    return {
        "success": True,
        "dateRanges": suggestions,
        "currentDate": today.strftime("%Y-%m-%d")
    }