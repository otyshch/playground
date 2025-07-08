"""
Test data factories for generating test data.
"""
import factory
from datetime import datetime, timedelta
from typing import Optional, List
import random

from src.shared.models import StateFiscalData, StateFiscalDataCreate, StateFiscalDataResponse, StateFiscalIndicators
from src.shared.config import US_STATE_CODES


class StateFiscalDataFactory(factory.Factory):
    """Factory for creating StateFiscalData model instances."""
    
    class Meta:
        model = StateFiscalData
    
    id = factory.Sequence(lambda n: n)
    state_code = factory.LazyFunction(lambda: random.choice(US_STATE_CODES))
    data_timestamp = factory.LazyFunction(lambda: datetime.now() - timedelta(days=random.randint(0, 365)))
    state_tax_receipts_yoy_growth = factory.LazyFunction(lambda: round(random.uniform(-10.0, 15.0), 2))
    state_budget_surplus_deficit_as_pct_of_gsp = factory.LazyFunction(lambda: round(random.uniform(-5.0, 3.0), 2))
    created_at = factory.LazyFunction(datetime.now)
    updated_at = factory.LazyFunction(datetime.now)


class StateFiscalDataCreateFactory(factory.Factory):
    """Factory for creating StateFiscalDataCreate model instances."""
    
    class Meta:
        model = StateFiscalDataCreate
    
    state_code = factory.LazyFunction(lambda: random.choice(US_STATE_CODES))
    data_timestamp = factory.LazyFunction(lambda: datetime.now() - timedelta(days=random.randint(0, 365)))
    state_tax_receipts_yoy_growth = factory.LazyFunction(lambda: round(random.uniform(-10.0, 15.0), 2))
    state_budget_surplus_deficit_as_pct_of_gsp = factory.LazyFunction(lambda: round(random.uniform(-5.0, 3.0), 2))


class StateFiscalIndicatorsFactory(factory.Factory):
    """Factory for creating StateFiscalIndicators model instances."""
    
    class Meta:
        model = StateFiscalIndicators
    
    state_tax_receipts_yoy_growth = factory.LazyFunction(lambda: round(random.uniform(-10.0, 15.0), 2))
    state_budget_surplus_deficit_as_pct_of_gsp = factory.LazyFunction(lambda: round(random.uniform(-5.0, 3.0), 2))


class StateFiscalDataResponseFactory(factory.Factory):
    """Factory for creating StateFiscalDataResponse model instances."""
    
    class Meta:
        model = StateFiscalDataResponse
    
    data_timestamp = factory.LazyFunction(lambda: datetime.now() - timedelta(days=random.randint(0, 365)))
    state = factory.LazyFunction(lambda: random.choice(US_STATE_CODES))
    state_fiscal_indicators = factory.SubFactory(StateFiscalIndicatorsFactory)


class TestDataBuilder:
    """Builder class for creating complex test data scenarios."""
    
    @staticmethod
    def create_historical_data_series(
        state_code: str, 
        start_date: datetime, 
        end_date: datetime, 
        frequency_days: int = 30
    ) -> List[StateFiscalData]:
        """Create a series of historical data points for a state."""
        records = []
        current_date = start_date
        
        while current_date <= end_date:
            record = StateFiscalDataFactory.create(
                state_code=state_code,
                data_timestamp=current_date
            )
            records.append(record)
            current_date += timedelta(days=frequency_days)
        
        return records
    
    @staticmethod
    def create_multi_state_data(
        states: List[str], 
        date: datetime, 
        variation: bool = False
    ) -> List[StateFiscalData]:
        """Create data for multiple states on the same date."""
        records = []
        
        for state in states:
            if variation:
                # Add some variation to make data more realistic
                growth = round(random.uniform(-5.0, 10.0), 2)
                deficit = round(random.uniform(-3.0, 2.0), 2)
            else:
                # Use consistent values for predictable testing
                growth = 3.5
                deficit = -1.2
            
            record = StateFiscalDataFactory.create(
                state_code=state,
                data_timestamp=date,
                state_tax_receipts_yoy_growth=growth,
                state_budget_surplus_deficit_as_pct_of_gsp=deficit
            )
            records.append(record)
        
        return records
    
    @staticmethod
    def create_edge_case_data() -> List[StateFiscalData]:
        """Create edge case data for testing boundary conditions."""
        edge_cases = [
            # Very high growth
            StateFiscalDataFactory.create(
                state_code="CA",
                data_timestamp=datetime(2023, 1, 1),
                state_tax_receipts_yoy_growth=50.0,
                state_budget_surplus_deficit_as_pct_of_gsp=5.0
            ),
            # Very negative growth
            StateFiscalDataFactory.create(
                state_code="NY",
                data_timestamp=datetime(2023, 1, 1),
                state_tax_receipts_yoy_growth=-25.0,
                state_budget_surplus_deficit_as_pct_of_gsp=-10.0
            ),
            # Zero values
            StateFiscalDataFactory.create(
                state_code="TX",
                data_timestamp=datetime(2023, 1, 1),
                state_tax_receipts_yoy_growth=0.0,
                state_budget_surplus_deficit_as_pct_of_gsp=0.0
            ),
            # Very small positive values
            StateFiscalDataFactory.create(
                state_code="FL",
                data_timestamp=datetime(2023, 1, 1),
                state_tax_receipts_yoy_growth=0.01,
                state_budget_surplus_deficit_as_pct_of_gsp=0.01
            ),
            # Very small negative values
            StateFiscalDataFactory.create(
                state_code="IL",
                data_timestamp=datetime(2023, 1, 1),
                state_tax_receipts_yoy_growth=-0.01,
                state_budget_surplus_deficit_as_pct_of_gsp=-0.01
            )
        ]
        
        return edge_cases
    
    @staticmethod
    def create_data_quality_scenarios() -> List[StateFiscalData]:
        """Create data scenarios for testing data quality metrics."""
        scenarios = []
        
        # Recent high-quality data
        for i, state in enumerate(["CA", "NY", "TX"]):
            record = StateFiscalDataFactory.create(
                state_code=state,
                data_timestamp=datetime.now() - timedelta(days=i),
                state_tax_receipts_yoy_growth=3.5 + i * 0.5,
                state_budget_surplus_deficit_as_pct_of_gsp=-1.2 - i * 0.2
            )
            scenarios.append(record)
        
        # Old data for freshness testing
        old_record = StateFiscalDataFactory.create(
            state_code="WA",
            data_timestamp=datetime.now() - timedelta(days=100),
            state_tax_receipts_yoy_growth=2.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-2.0
        )
        scenarios.append(old_record)
        
        return scenarios
    
    @staticmethod
    def create_performance_test_data(
        num_states: int = 10, 
        num_records_per_state: int = 100
    ) -> List[StateFiscalData]:
        """Create large dataset for performance testing."""
        records = []
        test_states = US_STATE_CODES[:num_states]
        
        for state in test_states:
            for i in range(num_records_per_state):
                record = StateFiscalDataFactory.create(
                    state_code=state,
                    data_timestamp=datetime.now() - timedelta(days=i * 7),  # Weekly data
                    state_tax_receipts_yoy_growth=round(random.uniform(-5.0, 8.0), 2),
                    state_budget_surplus_deficit_as_pct_of_gsp=round(random.uniform(-3.0, 2.0), 2)
                )
                records.append(record)
        
        return records


class MockAPIResponseFactory:
    """Factory for creating mock API responses."""
    
    @staticmethod
    def create_fred_observations_response(num_observations: int = 5) -> dict:
        """Create mock FRED API observations response."""
        observations = []
        
        for i in range(num_observations):
            date = (datetime.now() - timedelta(days=i * 30)).strftime("%Y-%m-%d")
            value = str(round(random.uniform(1000.0, 5000.0), 1))
            
            observations.append({
                "date": date,
                "value": value
            })
        
        return {"observations": observations}
    
    @staticmethod
    def create_fred_empty_response() -> dict:
        """Create mock empty FRED API response."""
        return {"observations": []}
    
    @staticmethod
    def create_fred_missing_values_response() -> dict:
        """Create mock FRED API response with missing values."""
        return {
            "observations": [
                {"date": "2023-01-01", "value": "1000.0"},
                {"date": "2023-02-01", "value": "."},  # Missing value
                {"date": "2023-03-01", "value": "1100.0"},
                {"date": "2023-04-01", "value": "."},  # Missing value
                {"date": "2023-05-01", "value": "1200.0"}
            ]
        }
    
    @staticmethod
    def create_successful_ingestion_response() -> dict:
        """Create successful data ingestion response."""
        return {
            "state_tax_receipts_yoy_growth": round(random.uniform(-5.0, 10.0), 2),
            "state_budget_surplus_deficit_as_pct_of_gsp": round(random.uniform(-3.0, 2.0), 2)
        }
    
    @staticmethod
    def create_api_error_response(status_code: int = 400, message: str = "Bad Request") -> dict:
        """Create mock API error response."""
        return {
            "error": {
                "status": status_code,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        }


class TestScenarioBuilder:
    """Builder for creating specific test scenarios."""
    
    @staticmethod
    def build_forward_fill_scenario() -> dict:
        """Build scenario for testing forward fill functionality."""
        # Create historical data that's recent enough for forward fill
        historical_date = datetime.now() - timedelta(days=15)
        target_date = datetime.now()
        
        historical_record = StateFiscalDataFactory.create(
            state_code="CA",
            data_timestamp=historical_date,
            state_tax_receipts_yoy_growth=4.2,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.8
        )
        
        return {
            "historical_record": historical_record,
            "target_date": target_date,
            "expected_values": {
                "state_tax_receipts_yoy_growth": 4.2,
                "state_budget_surplus_deficit_as_pct_of_gsp": -1.8
            }
        }
    
    @staticmethod
    def build_data_gap_scenario() -> dict:
        """Build scenario for testing data gap handling."""
        # Create data with gaps for testing interpolation/handling
        records = []
        
        # Data points with gaps
        dates_with_data = [
            datetime(2023, 1, 1),
            datetime(2023, 3, 1),  # Missing February
            datetime(2023, 5, 1),  # Missing April
            datetime(2023, 7, 1)   # Missing June
        ]
        
        for date in dates_with_data:
            record = StateFiscalDataFactory.create(
                state_code="CA",
                data_timestamp=date
            )
            records.append(record)
        
        missing_dates = [
            datetime(2023, 2, 1),
            datetime(2023, 4, 1),
            datetime(2023, 6, 1)
        ]
        
        return {
            "records_with_data": records,
            "missing_dates": missing_dates,
            "date_range": {
                "start": datetime(2023, 1, 1),
                "end": datetime(2023, 7, 1)
            }
        }
    
    @staticmethod
    def build_bulk_export_scenario() -> dict:
        """Build scenario for testing bulk export functionality."""
        # Create data for multiple states and dates
        states = ["CA", "NY", "TX", "FL"]
        dates = [
            datetime(2023, 12, 31),
            datetime(2023, 11, 30),
            datetime(2023, 10, 31)
        ]
        
        records = []
        for state in states:
            for date in dates:
                record = StateFiscalDataFactory.create(
                    state_code=state,
                    data_timestamp=date
                )
                records.append(record)
        
        return {
            "records": records,
            "states": states,
            "date_range": {
                "start": min(dates),
                "end": max(dates)
            },
            "expected_record_count": len(states) * len(dates)
        }
    
    @staticmethod
    def build_api_rate_limit_scenario() -> dict:
        """Build scenario for testing API rate limiting."""
        return {
            "requests_to_make": 150,  # Above typical rate limit
            "expected_rate_limit": 100,
            "time_window": 60,  # seconds
            "expected_blocked_requests": 50
        }


class DatabaseTestHelper:
    """Helper class for database testing operations."""
    
    @staticmethod
    def populate_test_database(session, scenario: str = "basic"):
        """Populate test database with predefined scenarios."""
        if scenario == "basic":
            records = [
                StateFiscalDataFactory.create(state_code="CA", data_timestamp=datetime(2023, 12, 31)),
                StateFiscalDataFactory.create(state_code="NY", data_timestamp=datetime(2023, 12, 31)),
                StateFiscalDataFactory.create(state_code="TX", data_timestamp=datetime(2023, 12, 31))
            ]
        elif scenario == "historical":
            records = TestDataBuilder.create_historical_data_series(
                "CA", 
                datetime(2023, 1, 1), 
                datetime(2023, 12, 31),
                frequency_days=30
            )
        elif scenario == "multi_state":
            records = TestDataBuilder.create_multi_state_data(
                ["CA", "NY", "TX", "FL", "IL"], 
                datetime(2023, 12, 31)
            )
        elif scenario == "edge_cases":
            records = TestDataBuilder.create_edge_case_data()
        elif scenario == "performance":
            records = TestDataBuilder.create_performance_test_data(5, 50)
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        session.add_all(records)
        session.commit()
        
        return records
    
    @staticmethod
    def cleanup_test_database(session, model_class=StateFiscalData):
        """Clean up test database."""
        session.query(model_class).delete()
        session.commit()
    
    @staticmethod
    def verify_database_state(session, expected_count: Optional[int] = None):
        """Verify database state for testing."""
        total_records = session.query(StateFiscalData).count()
        
        if expected_count is not None:
            assert total_records == expected_count
        
        return {
            "total_records": total_records,
            "states_with_data": session.query(StateFiscalData.state_code).distinct().count(),
            "latest_timestamp": session.query(StateFiscalData.data_timestamp).order_by(
                StateFiscalData.data_timestamp.desc()
            ).first(),
            "earliest_timestamp": session.query(StateFiscalData.data_timestamp).order_by(
                StateFiscalData.data_timestamp.asc()
            ).first()
        }