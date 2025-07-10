from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import re

class GA4QueryInput(BaseModel):
    user_id: str = Field(..., description="User ID to identify whose GA4 tokens to use")
    dimensions: List[str] = Field(default=[], description="GA4 dimension names (e.g., ['date', 'country', 'pagePath'])")
    metrics: List[str] = Field(..., description="GA4 metric names (e.g., ['sessions', 'pageviews', 'users'])")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format (e.g., '2025-06-09')")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format (e.g., '2025-07-08')")
    limit: Optional[int] = Field(default=10000, description="Maximum number of rows to return (default: 100)")
    property_id: Optional[str] = Field(default=None, description="Override GA4 property ID if needed")
    
    filters: Optional[dict] = Field(default=None, description="Filter expressions for dimensions and metrics (GA4 API FilterExpression)")
    order_by: Optional[List[dict]] = Field(default=None, description="List of order by clauses (GA4 API OrderBy objects)")
    currency_code: Optional[str] = Field(default=None, description="Currency code for monetary metrics (e.g., 'USD')")
    granularity: Optional[str] = Field(default="daily", description="Granularity for date-based queries (e.g., 'daily', 'weekly', 'monthly')")
    include_empty_rows: Optional[bool] = Field(default=False, description="Whether to include rows with zero values")

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        """Validate date format is YYYY-MM-DD"""
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('Date must be in YYYY-MM-DD format')
        
        # Try to parse the date to ensure it's valid
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Invalid date')
        
        return v

    @validator('metrics')
    def validate_metrics_not_empty(cls, v):
        """Ensure at least one metric is provided"""
        if not v:
            raise ValueError('At least one metric must be specified')
        return v

    @validator('limit')
    def validate_limit(cls, v):
        """Ensure limit is within reasonable bounds"""
        if v is not None and (v < 1 or v > 10000):
            raise ValueError('Limit must be between 1 and 10000')
        return v

    @validator('user_id')
    def validate_user_id(cls, v):
        """Ensure user_id is not empty"""
        if not v or not v.strip():
            raise ValueError('User ID cannot be empty')
        return v.strip()

class BasicQueryInput(BaseModel):
    user_id: str = Field(..., description="User ID to identify whose GA4 tokens to use")
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Ensure user_id is not empty"""
        if not v or not v.strip():
            raise ValueError('User ID cannot be empty')
        return v.strip()