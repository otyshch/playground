"""
Core data ingestion service for state fiscal data.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import desc, and_
from ..shared.database import get_database_manager
from ..shared.models import StateFiscalData, StateFiscalDataCreate
from ..shared.config import get_settings, US_STATE_CODES
from .free_apis import FreeDataFetcher

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Custom exception for data validation errors."""
    pass


class StateFiscalDataService:
    """Service for managing state fiscal data ingestion and storage."""

    def __init__(self):
        self.settings = get_settings()
        self.db_manager = get_database_manager()
        self.data_fetcher = FreeDataFetcher(
            fred_api_key=self.settings.fred_api_key,
        )


    def check_historical_data_exists(self, days_back: int = 365) -> Dict[str, bool]:
        """
        Check if historical data exists for all states.

        Args:
            days_back: Number of days back to check

        Returns:
            Dictionary mapping state codes to whether they have sufficient historical data
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)

        with self.db_manager.get_session_sync() as session:
            results = {}

            for state_code in US_STATE_CODES:
                # Count records for this state within the time period
                count = session.query(StateFiscalData).filter(
                    and_(
                        StateFiscalData.state_code == state_code,
                        StateFiscalData.data_timestamp >= cutoff_date
                    )
                ).count()

                # Consider sufficient if we have at least 6 records (roughly monthly)
                results[state_code] = count >= 6

            return results

    async def initialize_startup_data(self, days_back: int = 365) -> Dict[str, any]:
        """
        Initialize historical data during startup if it doesn't exist.

        Args:
            days_back: Number of days back to populate

        Returns:
            Dictionary with initialization results
        """
        logger.info("🚀 Checking for historical data during startup...")

        # Check if historical data exists
        data_status = self.check_historical_data_exists(days_back)

        states_with_data = [state for state, has_data in data_status.items() if has_data]
        states_without_data = [state for state, has_data in data_status.items() if not has_data]

        logger.info(f"📊 Data status: {len(states_with_data)} states have data, {len(states_without_data)} need population")

        population_results = {}

        if states_without_data:
            logger.info(f"📥 Populating historical data for {len(states_without_data)} states...")

            # Only populate for states that need data
            targeted_results = {}
            for state_code in states_without_data:
                try:
                    # Generate monthly dates for this state (going backwards from today)
                    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    start_date = end_date - timedelta(days=days_back)

                    current_date = end_date
                    state_created = 0

                    # Go back month by month from today
                    while current_date >= start_date:
                        if not self._data_exists(state_code, current_date):
                            success = await self.ingest_state_data(state_code, current_date)
                            if success:
                                state_created += 1

                            # Small delay to avoid API rate limits
                            await asyncio.sleep(0.2)

                        # Move to previous month
                        if current_date.month == 1:
                            current_date = current_date.replace(year=current_date.year - 1, month=12)
                        else:
                            current_date = current_date.replace(month=current_date.month - 1)

                    targeted_results[state_code] = state_created
                    logger.info(f"✅ Created {state_created} records for {state_code}")

                except Exception as e:
                    logger.error(f"❌ Error populating data for {state_code}: {e}")
                    targeted_results[state_code] = 0

            population_results = targeted_results
        else:
            logger.info("✅ All states already have sufficient historical data")

        total_created = sum(population_results.values())

        return {
            "startup_check_completed": True,
            "states_with_data": len(states_with_data),
            "states_populated": len(states_without_data),
            "total_records_created": total_created,
            "population_results": population_results,
            "days_back": days_back
        }

    async def populate_state_data(self, state_code: str, days_back: int = 365) -> Dict[str, any]:
        """
        Populate historical data for a specific state.

        Args:
            state_code: Two-letter state code
            days_back: Number of days back to populate (default: 365 for 1 year)

        Returns:
            Dictionary with population results for the state
        """
        if state_code not in US_STATE_CODES:
            raise ValueError(f"Invalid state code: {state_code}")

        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=days_back)

        logger.info(f"Starting data population for {state_code} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        # Generate monthly data points going backwards from today
        dates_to_populate = []
        current_date = end_date

        # Go back month by month from today until we reach start_date
        while current_date >= start_date:
            dates_to_populate.append(current_date)

            # Move to previous month
            if current_date.month == 1:
                current_date = current_date.replace(year=current_date.year - 1, month=12)
            else:
                current_date = current_date.replace(month=current_date.month - 1)

        # Reverse to get chronological order (oldest first)
        dates_to_populate.reverse()

        logger.info(f"Will populate {len(dates_to_populate)} monthly data points for {state_code}")

        records_created = 0

        for target_date in dates_to_populate:
            try:
                # Check if data already exists
                if not self._data_exists(state_code, target_date):
                    success = await self.ingest_state_data(state_code, target_date)
                    if success:
                        records_created += 1

                    # Small delay to avoid overwhelming APIs
                    await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error populating data for {state_code} on {target_date}: {e}")

        logger.info(f"Data population completed for {state_code}: {records_created} records created")

        return {
            "state_code": state_code,
            "records_processed": records_created,
            "dates_processed": len(dates_to_populate),
            "days_back": days_back,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d')
        }


    async def ingest_state_data(self, state_code: str, target_date: datetime) -> bool:
        """
        Ingest fiscal data for a specific state.

        Args:
            state_code: Two-letter state code
            target_date: Target date for data ingestion

        Returns:
            True if ingestion was successful, False otherwise
        """
        try:
            # Check if data already exists for this state and date
            if self._data_exists(state_code, target_date):
                logger.info(f"Data already exists for {state_code} on {target_date}")
                return True

            # Fetch data from external APIs using improved FreeDataFetcher
            fiscal_data = await self.data_fetcher.fetch_state_fiscal_data(state_code, target_date)
            indicators = self.data_fetcher.calculate_fiscal_indicators(fiscal_data)

            if not indicators or not any(v is not None for v in indicators.values()):
                logger.warning(f"No data retrieved for {state_code} on {target_date}")

                # Apply forward-fill logic if enabled
                if self.settings.enable_forward_fill:
                    return self._apply_forward_fill(state_code, target_date)
                return False

            # Validate data
            if self.settings.enable_data_validation:
                self._validate_indicators(indicators, state_code, target_date)

            # Create data record
            fiscal_data = StateFiscalDataCreate(
                state_code=state_code,
                data_timestamp=target_date,
                state_tax_receipts_yoy_growth=indicators["state_tax_receipts_yoy_growth"],
                state_budget_surplus_deficit_as_pct_of_gsp=indicators["state_budget_surplus_deficit_as_pct_of_gsp"]
            )

            # Store in database
            self._store_fiscal_data(fiscal_data)

            logger.info(f"Successfully ingested data for {state_code} on {target_date}")
            return True

        except Exception as e:
            logger.error(f"Failed to ingest data for {state_code} on {target_date}: {e}")
            return False

    def _data_exists(self, state_code: str, target_date: datetime) -> bool:
        """Check if data already exists for the given state and date."""
        with self.db_manager.get_session_sync() as session:
            existing = session.query(StateFiscalData).filter(
                and_(
                    StateFiscalData.state_code == state_code,
                    StateFiscalData.data_timestamp == target_date
                )
            ).first()
            return existing is not None

    def _validate_indicators(self, indicators: Dict[str, float], state_code: str, target_date: datetime):
        """
        Validate fiscal indicator values.

        Args:
            indicators: Dictionary of fiscal indicators
            state_code: State code for context
            target_date: Target date for context

        Raises:
            DataValidationError: If validation fails
        """
        required_keys = [
            "state_tax_receipts_yoy_growth",
            "state_budget_surplus_deficit_as_pct_of_gsp"
        ]

        # Check required fields
        for key in required_keys:
            if key not in indicators:
                raise DataValidationError(f"Missing required indicator: {key}")

            value = indicators[key]
            if not isinstance(value, (int, float)):
                raise DataValidationError(f"Invalid data type for {key}: {type(value)}")

            # Check for reasonable value ranges
            if key == "state_tax_receipts_yoy_growth":
                if abs(value) > 1000:  # YoY growth should be reasonable
                    logger.warning(f"Unusual tax receipt growth for {state_code}: {value}%")

            elif key == "state_budget_surplus_deficit_as_pct_of_gsp":
                if abs(value) > 50:  # Budget balance should be reasonable percentage of GSP
                    logger.warning(f"Unusual budget balance for {state_code}: {value}% of GSP")

        logger.debug(f"Data validation passed for {state_code} on {target_date}")

    def _store_fiscal_data(self, fiscal_data: StateFiscalDataCreate):
        """Store fiscal data in the database."""
        with self.db_manager.get_session_sync() as session:
            db_record = StateFiscalData(**fiscal_data.model_dump())
            session.add(db_record)
            session.commit()
            logger.debug(f"Stored fiscal data: {fiscal_data}")

    def _apply_forward_fill(self, state_code: str, target_date: datetime) -> bool:
        """
        Apply forward-fill logic when current data is not available.

        Args:
            state_code: Two-letter state code
            target_date: Target date for data

        Returns:
            True if forward-fill was successful, False otherwise
        """
        try:
            # Find the most recent data for this state
            with self.db_manager.get_session_sync() as session:
                latest_record = session.query(StateFiscalData).filter(
                    and_(
                        StateFiscalData.state_code == state_code,
                        StateFiscalData.data_timestamp < target_date
                    )
                ).order_by(desc(StateFiscalData.data_timestamp)).first()

                if latest_record is None:
                    logger.warning(f"No historical data found for forward-fill: {state_code}")
                    return False

                # Check if the latest data is not too old (within 90 days)
                days_old = (target_date - latest_record.data_timestamp).days
                if days_old > 90:
                    logger.warning(f"Latest data too old for forward-fill: {days_old} days")
                    return False

                # Create new record with forward-filled values
                forward_filled_data = StateFiscalDataCreate(
                    state_code=state_code,
                    data_timestamp=target_date,
                    state_tax_receipts_yoy_growth=latest_record.state_tax_receipts_yoy_growth,
                    state_budget_surplus_deficit_as_pct_of_gsp=latest_record.state_budget_surplus_deficit_as_pct_of_gsp
                )

                self._store_fiscal_data(forward_filled_data)

                logger.info(f"Applied forward-fill for {state_code} on {target_date} "
                           f"using data from {latest_record.data_timestamp}")
                return True

        except Exception as e:
            logger.error(f"Failed to apply forward-fill for {state_code}: {e}")
            return False

    def get_latest_data(self, state_code: str, before_date: Optional[datetime] = None) -> Optional[StateFiscalData]:
        """
        Get the latest fiscal data for a state.

        Args:
            state_code: Two-letter state code
            before_date: Get latest data before this date (optional)

        Returns:
            Latest fiscal data record or None
        """
        with self.db_manager.get_session_sync() as session:
            query = session.query(StateFiscalData).filter(
                StateFiscalData.state_code == state_code
            )

            if before_date:
                query = query.filter(StateFiscalData.data_timestamp <= before_date)

            latest_record = query.order_by(desc(StateFiscalData.data_timestamp)).first()
            return latest_record

    def get_data_range(self, state_code: str, start_date: datetime, end_date: datetime) -> List[StateFiscalData]:
        """
        Get fiscal data for a state within a date range.

        Args:
            state_code: Two-letter state code
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of fiscal data records
        """
        with self.db_manager.get_session_sync() as session:
            records = session.query(StateFiscalData).filter(
                and_(
                    StateFiscalData.state_code == state_code,
                    StateFiscalData.data_timestamp >= start_date,
                    StateFiscalData.data_timestamp <= end_date
                )
            ).order_by(StateFiscalData.data_timestamp).all()

            return records

    def cleanup_old_data(self, retention_days: Optional[int] = None) -> int:
        """
        Remove old fiscal data beyond retention period.

        Args:
            retention_days: Number of days to retain (defaults to config value)

        Returns:
            Number of records deleted
        """
        if retention_days is None:
            retention_days = self.settings.data_retention_days

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        with self.db_manager.get_session_sync() as session:
            deleted_count = session.query(StateFiscalData).filter(
                StateFiscalData.data_timestamp < cutoff_date
            ).delete()

            session.commit()

            logger.info(f"Cleaned up {deleted_count} old fiscal data records")
            return deleted_count

    def get_ingestion_status(self) -> Dict[str, any]:
        """
        Get current ingestion status and statistics.

        Returns:
            Dictionary containing ingestion status information
        """
        with self.db_manager.get_session_sync() as session:
            # Count total records
            total_records = session.query(StateFiscalData).count()

            # Count records by state
            state_counts = {}
            for state_code in US_STATE_CODES:
                count = session.query(StateFiscalData).filter(
                    StateFiscalData.state_code == state_code
                ).count()
                state_counts[state_code] = count

            # Get latest data timestamp
            latest_record = session.query(StateFiscalData).order_by(
                desc(StateFiscalData.data_timestamp)
            ).first()

            latest_timestamp = latest_record.data_timestamp if latest_record else None

            return {
                "total_records": total_records,
                "state_counts": state_counts,
                "latest_timestamp": latest_timestamp,
                "states_with_data": len([s for s, c in state_counts.items() if c > 0]),
                "retention_days": self.settings.data_retention_days,
                "forward_fill_enabled": self.settings.enable_forward_fill,
                "validation_enabled": self.settings.enable_data_validation
            }
