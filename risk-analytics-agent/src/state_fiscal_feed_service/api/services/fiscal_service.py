"""
Business logic service for fiscal data operations.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import and_, desc, asc

from ...shared.database import get_database_manager
from ...shared.models import StateFiscalData
from ...shared.config import US_STATE_CODES

logger = logging.getLogger(__name__)


class FiscalDataService:
    """Service class for fiscal data business logic."""

    def __init__(self):
        self.db_manager = get_database_manager()

    async def get_latest_data(self, state_code: str, before_date: datetime) -> Optional[StateFiscalData]:
        """
        Get the latest fiscal data for a state on or before the specified date.

        Args:
            state_code: Two-letter state code
            before_date: Get latest data on or before this date

        Returns:
            Latest fiscal data record or None
        """
        if state_code not in US_STATE_CODES:
            raise ValueError(f"Invalid state code: {state_code}")

        with self.db_manager.get_session_sync() as session:
            record = session.query(StateFiscalData).filter(
                and_(
                    StateFiscalData.state_code == state_code,
                    StateFiscalData.data_timestamp <= before_date
                )
            ).order_by(desc(StateFiscalData.data_timestamp)).first()

            return record

    async def get_state_history(
        self,
        state_code: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[StateFiscalData]:
        """
        Get historical fiscal data for a state within a date range.

        Args:
            state_code: Two-letter state code
            start_date: Start date (optional)
            end_date: End date (optional)
            limit: Maximum number of records to return

        Returns:
            List of fiscal data records
        """
        if state_code not in US_STATE_CODES:
            raise ValueError(f"Invalid state code: {state_code}")

        with self.db_manager.get_session_sync() as session:
            query = session.query(StateFiscalData).filter(
                StateFiscalData.state_code == state_code
            )

            if start_date:
                query = query.filter(StateFiscalData.data_timestamp >= start_date)

            if end_date:
                query = query.filter(StateFiscalData.data_timestamp <= end_date)

            records = query.order_by(desc(StateFiscalData.data_timestamp)).limit(limit).all()

            return records

    async def get_bulk_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        states: Optional[List[str]] = None
    ) -> List[StateFiscalData]:
        """
        Get bulk fiscal data for multiple states and date range.

        Args:
            start_date: Start date (optional)
            end_date: End date (optional)
            states: List of state codes (optional, defaults to all states)

        Returns:
            List of fiscal data records
        """
        with self.db_manager.get_session_sync() as session:
            query = session.query(StateFiscalData)

            if start_date:
                query = query.filter(StateFiscalData.data_timestamp >= start_date)

            if end_date:
                query = query.filter(StateFiscalData.data_timestamp <= end_date)

            if states:
                # Validate state codes
                invalid_states = [s for s in states if s not in US_STATE_CODES]
                if invalid_states:
                    raise ValueError(f"Invalid state codes: {invalid_states}")

                query = query.filter(StateFiscalData.state_code.in_(states))

            # Order by state and timestamp for consistent export
            records = query.order_by(
                StateFiscalData.state_code,
                StateFiscalData.data_timestamp
            ).all()

            return records

    async def get_latest_by_states(self, states: Optional[List[str]] = None) -> List[StateFiscalData]:
        """
        Get the latest fiscal data for multiple states.

        Args:
            states: List of state codes (optional, defaults to all states)

        Returns:
            List of latest fiscal data records for each state
        """
        if states is None:
            states = US_STATE_CODES
        else:
            # Validate state codes
            invalid_states = [s for s in states if s not in US_STATE_CODES]
            if invalid_states:
                raise ValueError(f"Invalid state codes: {invalid_states}")

        latest_records = []

        with self.db_manager.get_session_sync() as session:
            for state_code in states:
                record = session.query(StateFiscalData).filter(
                    StateFiscalData.state_code == state_code
                ).order_by(desc(StateFiscalData.data_timestamp)).first()

                if record:
                    latest_records.append(record)

        return latest_records

    async def get_comparative_data(
        self,
        states: List[str],
        target_date: datetime
    ) -> List[StateFiscalData]:
        """
        Get fiscal data for multiple states for the same date for comparison.

        Args:
            states: List of state codes to compare
            target_date: Target date for comparison

        Returns:
            List of fiscal data records for the specified states and date
        """
        # Validate state codes
        invalid_states = [s for s in states if s not in US_STATE_CODES]
        if invalid_states:
            raise ValueError(f"Invalid state codes: {invalid_states}")

        comparative_data = []

        with self.db_manager.get_session_sync() as session:
            for state_code in states:
                # Get latest data on or before target date
                record = session.query(StateFiscalData).filter(
                    and_(
                        StateFiscalData.state_code == state_code,
                        StateFiscalData.data_timestamp <= target_date
                    )
                ).order_by(desc(StateFiscalData.data_timestamp)).first()

                if record:
                    comparative_data.append(record)

        return comparative_data

    async def get_data_summary(self) -> dict:
        """
        Get summary statistics about the fiscal data.

        Returns:
            Dictionary containing summary statistics
        """
        with self.db_manager.get_session_sync() as session:
            # Total records
            total_records = session.query(StateFiscalData).count()

            # States with data
            states_with_data = session.query(StateFiscalData.state_code).distinct().count()

            # Date range
            earliest_record = session.query(StateFiscalData).order_by(
                asc(StateFiscalData.data_timestamp)
            ).first()

            latest_record = session.query(StateFiscalData).order_by(
                desc(StateFiscalData.data_timestamp)
            ).first()

            # Recent data (last 30 days)
            recent_cutoff = datetime.now() - timedelta(days=30)
            recent_records = session.query(StateFiscalData).filter(
                StateFiscalData.data_timestamp >= recent_cutoff
            ).count()

            return {
                "total_records": total_records,
                "states_with_data": states_with_data,
                "total_states": len(US_STATE_CODES),
                "coverage_percentage": round((states_with_data / len(US_STATE_CODES)) * 100, 2),
                "earliest_date": earliest_record.data_timestamp.isoformat() if earliest_record else None,
                "latest_date": latest_record.data_timestamp.isoformat() if latest_record else None,
                "recent_records_30_days": recent_records,
                "data_freshness_days": (datetime.now() - latest_record.data_timestamp).days if latest_record else None
            }
