"""
Shared data models for the State Fiscal Feed system.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, DateTime, Float, Integer, String, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field

Base = declarative_base()


class StateFiscalData(Base):
    """SQLAlchemy model for state fiscal data."""
    
    __tablename__ = "state_fiscal_data"
    
    id = Column(Integer, primary_key=True, index=True)
    state_code = Column(String(2), nullable=False, index=True)
    data_timestamp = Column(DateTime, nullable=False, index=True)
    state_tax_receipts_yoy_growth = Column(Float, nullable=False)
    state_budget_surplus_deficit_as_pct_of_gsp = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_state_timestamp', 'state_code', 'data_timestamp'),
        Index('idx_data_timestamp', 'data_timestamp'),
    )


# Pydantic models for API serialization
class StateFiscalIndicators(BaseModel):
    """State fiscal indicators data."""
    
    state_tax_receipts_yoy_growth: float = Field(
        ..., 
        description="Year-over-year growth in total tax receipts for the state"
    )
    state_budget_surplus_deficit_as_pct_of_gsp: float = Field(
        ..., 
        description="State budget surplus or deficit as percentage of GSP"
    )


class StateFiscalDataResponse(BaseModel):
    """Response model for state fiscal data API."""
    
    data_timestamp: datetime = Field(
        ..., 
        description="Timestamp of the fiscal data"
    )
    state: str = Field(
        ..., 
        max_length=2,
        description="Two-letter state postal code"
    )
    state_fiscal_indicators: StateFiscalIndicators


class StateFiscalDataCreate(BaseModel):
    """Model for creating new state fiscal data."""
    
    state_code: str = Field(..., max_length=2)
    data_timestamp: datetime
    state_tax_receipts_yoy_growth: float
    state_budget_surplus_deficit_as_pct_of_gsp: float


class BulkExportRequest(BaseModel):
    """Request model for bulk data export."""
    
    format: str = Field(default="csv", description="Export format (csv, json)")
    start_date: Optional[datetime] = Field(None, description="Start date for export")
    end_date: Optional[datetime] = Field(None, description="End date for export")
    states: Optional[list[str]] = Field(None, description="List of state codes to include")


# External API response models
class TradingEconomicsResponse(BaseModel):
    """Model for Trading Economics API response."""
    
    country: str
    category: str
    datetime: str
    value: float
    frequency: str
    historical_data_symbol: str
    last_update: str


class FREDResponse(BaseModel):
    """Model for FRED API response."""
    
    realtime_start: str
    realtime_end: str
    observation_start: str
    observation_end: str
    units: str
    output_type: int
    file_type: str
    order_by: str
    sort_order: str
    count: int
    offset: int
    limit: int
    observations: list[dict]


# Configuration models
class DatabaseConfig(BaseModel):
    """Database configuration."""
    
    url: str
    pool_size: int = 20
    max_overflow: int = 0
    pool_pre_ping: bool = True
    pool_recycle: int = 3600


class APIConfig(BaseModel):
    """API configuration."""
    
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    workers: int = 1
    cors_origins: list[str] = ["*"]
    rate_limit_per_minute: int = 100


class IngestionConfig(BaseModel):
    """Data ingestion configuration."""
    
    trading_economics_api_key: str
    fred_api_key: str
    schedule_minutes: int = 60
    batch_size: int = 100
    retry_attempts: int = 3
    retry_delay: int = 60  # seconds
    enable_forward_fill: bool = True
    data_retention_days: int = 2555  # ~7 years