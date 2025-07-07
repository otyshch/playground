"""
Metrics endpoints for monitoring and observability.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from ...shared.database import get_db
from ...shared.models import StateFiscalData
from ...shared.config import US_STATE_CODES

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", summary="Prometheus metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """Prometheus-formatted metrics endpoint."""
    try:
        metrics = []
        
        # Total records metric
        total_records = db.query(StateFiscalData).count()
        metrics.append(f"state_fiscal_data_total_records {total_records}")
        
        # Records by state
        for state_code in US_STATE_CODES:
            count = db.query(StateFiscalData).filter(
                StateFiscalData.state_code == state_code
            ).count()
            metrics.append(f'state_fiscal_data_records_by_state{{state="{state_code}"}} {count}')
        
        # Latest data timestamp
        latest_record = db.query(StateFiscalData).order_by(
            StateFiscalData.data_timestamp.desc()
        ).first()
        
        if latest_record:
            latest_timestamp = int(latest_record.data_timestamp.timestamp())
            metrics.append(f"state_fiscal_data_latest_timestamp {latest_timestamp}")
        
        # Data freshness (days since latest data)
        if latest_record:
            days_since_latest = (datetime.now() - latest_record.data_timestamp).days
            metrics.append(f"state_fiscal_data_freshness_days {days_since_latest}")
        
        # States with data
        states_with_data = db.query(StateFiscalData.state_code).distinct().count()
        metrics.append(f"state_fiscal_data_states_count {states_with_data}")
        
        return "\n".join(metrics)
        
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return "# Error generating metrics"


@router.get("/stats", summary="Detailed statistics")
async def get_statistics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Detailed statistics about the fiscal data."""
    try:
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "overview": {},
            "by_state": {},
            "data_quality": {},
            "time_series": {}
        }
        
        # Overview statistics
        total_records = db.query(StateFiscalData).count()
        states_with_data = db.query(StateFiscalData.state_code).distinct().count()
        
        latest_record = db.query(StateFiscalData).order_by(
            StateFiscalData.data_timestamp.desc()
        ).first()
        
        oldest_record = db.query(StateFiscalData).order_by(
            StateFiscalData.data_timestamp.asc()
        ).first()
        
        stats["overview"] = {
            "total_records": total_records,
            "states_with_data": states_with_data,
            "total_states": len(US_STATE_CODES),
            "coverage_percentage": round((states_with_data / len(US_STATE_CODES)) * 100, 2),
            "latest_data_date": latest_record.data_timestamp.isoformat() if latest_record else None,
            "oldest_data_date": oldest_record.data_timestamp.isoformat() if oldest_record else None,
            "data_span_days": (latest_record.data_timestamp - oldest_record.data_timestamp).days if latest_record and oldest_record else 0
        }
        
        # Statistics by state
        for state_code in US_STATE_CODES:
            state_stats = db.query(
                func.count(StateFiscalData.id),
                func.min(StateFiscalData.data_timestamp),
                func.max(StateFiscalData.data_timestamp),
                func.avg(StateFiscalData.state_tax_receipts_yoy_growth),
                func.avg(StateFiscalData.state_budget_surplus_deficit_as_pct_of_gsp)
            ).filter(
                StateFiscalData.state_code == state_code
            ).first()
            
            if state_stats[0] > 0:  # Has data
                stats["by_state"][state_code] = {
                    "record_count": state_stats[0],
                    "earliest_date": state_stats[1].isoformat() if state_stats[1] else None,
                    "latest_date": state_stats[2].isoformat() if state_stats[2] else None,
                    "avg_tax_growth": round(float(state_stats[3]) if state_stats[3] else 0, 2),
                    "avg_budget_pct_gsp": round(float(state_stats[4]) if state_stats[4] else 0, 2)
                }
        
        # Data quality metrics
        recent_date = datetime.now() - timedelta(days=30)
        recent_records = db.query(StateFiscalData).filter(
            StateFiscalData.data_timestamp >= recent_date
        ).count()
        
        stats["data_quality"] = {
            "recent_records_30_days": recent_records,
            "data_freshness_score": min(100, (recent_records / (len(US_STATE_CODES) * 30)) * 100) if recent_records > 0 else 0
        }
        
        # Time series aggregates
        monthly_counts = db.query(
            func.date_trunc('month', StateFiscalData.data_timestamp).label('month'),
            func.count(StateFiscalData.id).label('count')
        ).group_by(
            func.date_trunc('month', StateFiscalData.data_timestamp)
        ).order_by('month').limit(12).all()
        
        stats["time_series"]["monthly_record_counts"] = [
            {
                "month": record.month.isoformat(),
                "count": record.count
            }
            for record in monthly_counts
        ]
        
        return stats
        
    except Exception as e:
        logger.error(f"Error generating statistics: {e}")
        return {
            "error": "Failed to generate statistics",
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/data-quality", summary="Data quality metrics")
async def get_data_quality(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Data quality and completeness metrics."""
    try:
        quality_metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "completeness": {},
            "freshness": {},
            "consistency": {}
        }
        
        # Completeness metrics
        total_possible_records = len(US_STATE_CODES) * 365  # Assuming daily data for 1 year
        actual_records = db.query(StateFiscalData).filter(
            StateFiscalData.data_timestamp >= datetime.now() - timedelta(days=365)
        ).count()
        
        quality_metrics["completeness"] = {
            "total_possible_records": total_possible_records,
            "actual_records": actual_records,
            "completeness_percentage": round((actual_records / total_possible_records) * 100, 2)
        }
        
        # Freshness metrics
        latest_record = db.query(StateFiscalData).order_by(
            StateFiscalData.data_timestamp.desc()
        ).first()
        
        if latest_record:
            days_since_latest = (datetime.now() - latest_record.data_timestamp).days
            quality_metrics["freshness"] = {
                "latest_data_date": latest_record.data_timestamp.isoformat(),
                "days_since_latest": days_since_latest,
                "freshness_score": max(0, 100 - (days_since_latest * 10))  # Decrease by 10 per day
            }
        
        # Consistency metrics (looking for outliers)
        outlier_tax_growth = db.query(StateFiscalData).filter(
            StateFiscalData.state_tax_receipts_yoy_growth > 100
        ).count()
        
        outlier_budget_pct = db.query(StateFiscalData).filter(
            StateFiscalData.state_budget_surplus_deficit_as_pct_of_gsp > 50
        ).count()
        
        quality_metrics["consistency"] = {
            "outlier_tax_growth_records": outlier_tax_growth,
            "outlier_budget_pct_records": outlier_budget_pct,
            "total_records": db.query(StateFiscalData).count()
        }
        
        return quality_metrics
        
    except Exception as e:
        logger.error(f"Error generating data quality metrics: {e}")
        return {
            "error": "Failed to generate data quality metrics",
            "timestamp": datetime.utcnow().isoformat()
        }