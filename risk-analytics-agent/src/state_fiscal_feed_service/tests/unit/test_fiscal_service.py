"""
Unit tests for fiscal data service.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.api.services.fiscal_service import FiscalDataService
from src.shared.models import StateFiscalData, StateFiscalDataResponse, StateFiscalIndicators
from src.shared.database import DatabaseManager


class TestFiscalDataService:
    """Test fiscal data service functionality."""
    
    @pytest.fixture
    def service(self, test_db_session):
        """Create service instance for testing."""
        service = FiscalDataService()
        
        # Mock database manager to use test session
        mock_db_manager = Mock(spec=DatabaseManager)
        mock_db_manager.get_session_sync.return_value.__enter__ = Mock(return_value=test_db_session)
        mock_db_manager.get_session_sync.return_value.__exit__ = Mock(return_value=None)
        
        service.db_manager = mock_db_manager
        return service
    
    def test_validate_state_code_valid(self, service):
        """Test validation of valid state codes."""
        valid_codes = ["CA", "NY", "TX", "FL", "DC"]
        
        for code in valid_codes:
            # Should not raise an exception
            service._validate_state_code(code)
    
    def test_validate_state_code_invalid(self, service):
        """Test validation of invalid state codes."""
        invalid_codes = ["INVALID", "CAL", "123", "", "ca", "ny"]
        
        for code in invalid_codes:
            with pytest.raises(ValueError, match="Invalid state code"):
                service._validate_state_code(code)
    
    def test_get_latest_fiscal_data_success(self, service, sample_fiscal_data):
        """Test successful retrieval of latest fiscal data."""
        target_date = datetime(2023, 12, 31)
        
        result = service.get_latest_fiscal_data("CA", target_date)
        
        assert result is not None
        assert isinstance(result, StateFiscalDataResponse)
        assert result.state == "CA"
        assert result.data_timestamp == target_date
        assert result.state_fiscal_indicators.state_tax_receipts_yoy_growth == 3.5
        assert result.state_fiscal_indicators.state_budget_surplus_deficit_as_pct_of_gsp == -1.2
    
    def test_get_latest_fiscal_data_not_found(self, service):
        """Test retrieval when no data exists."""
        target_date = datetime(2024, 1, 1)
        
        result = service.get_latest_fiscal_data("WY", target_date)
        
        assert result is None
    
    def test_get_latest_fiscal_data_before_date(self, service, sample_fiscal_data):
        """Test retrieval of latest data before specific date."""
        # Request data before latest date
        target_date = datetime(2023, 12, 15)
        
        result = service.get_latest_fiscal_data("CA", target_date)
        
        assert result is not None
        assert result.state == "CA"
        # Should return November data (latest before target date)
        assert result.data_timestamp == datetime(2023, 11, 30)
    
    def test_get_historical_data_success(self, service, sample_fiscal_data):
        """Test successful retrieval of historical data."""
        start_date = datetime(2023, 10, 1)
        end_date = datetime(2023, 12, 31)
        
        result = service.get_historical_data("CA", start_date, end_date)
        
        assert "state" in result
        assert "records" in result
        assert "record_count" in result
        assert "date_range" in result
        
        assert result["state"] == "CA"
        assert result["record_count"] == 3  # CA has 3 records in this range
        assert len(result["records"]) == 3
        
        # Records should be sorted by timestamp (newest first)
        timestamps = [record["data_timestamp"] for record in result["records"]]
        assert timestamps == sorted(timestamps, reverse=True)
    
    def test_get_historical_data_with_limit(self, service, sample_fiscal_data):
        """Test historical data retrieval with limit."""
        start_date = datetime(2023, 10, 1)
        end_date = datetime(2023, 12, 31)
        limit = 2
        
        result = service.get_historical_data("CA", start_date, end_date, limit=limit)
        
        assert result["record_count"] == 3  # Total available records
        assert len(result["records"]) == 2  # Limited to 2 records
    
    def test_get_historical_data_with_offset(self, service, sample_fiscal_data):
        """Test historical data retrieval with offset."""
        start_date = datetime(2023, 10, 1)
        end_date = datetime(2023, 12, 31)
        offset = 1
        
        result = service.get_historical_data("CA", start_date, end_date, offset=offset)
        
        assert result["record_count"] == 3  # Total available records
        assert len(result["records"]) == 2  # Skipped first record
    
    def test_get_historical_data_no_data(self, service):
        """Test historical data retrieval when no data exists."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        result = service.get_historical_data("WY", start_date, end_date)
        
        assert result["state"] == "WY"
        assert result["record_count"] == 0
        assert len(result["records"]) == 0
    
    def test_get_bulk_data_all_states(self, service, sample_fiscal_data):
        """Test bulk data retrieval for all states."""
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        
        result = service.get_bulk_data(
            start_date=start_date,
            end_date=end_date
        )
        
        assert "records" in result
        assert "record_count" in result
        assert "states" in result
        
        assert result["record_count"] >= 3  # At least CA, NY, TX
        assert len(result["states"]) >= 3
        
        # Check record format
        for record in result["records"]:
            assert "timestamp" in record
            assert "state" in record
            assert "state_tax_receipts_yoy_growth" in record
            assert "state_budget_surplus_deficit_as_pct_of_gsp" in record
    
    def test_get_bulk_data_specific_states(self, service, sample_fiscal_data):
        """Test bulk data retrieval for specific states."""
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        states = ["CA", "NY"]
        
        result = service.get_bulk_data(
            states=states,
            start_date=start_date,
            end_date=end_date
        )
        
        assert result["record_count"] == 2  # Only CA and NY
        assert set(result["states"]) == set(states)
        
        # All records should be from requested states
        for record in result["records"]:
            assert record["state"] in states
    
    def test_get_bulk_data_invalid_states(self, service):
        """Test bulk data retrieval with invalid states."""
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        states = ["INVALID", "ALSO_INVALID"]
        
        with pytest.raises(ValueError, match="Invalid state codes"):
            service.get_bulk_data(
                states=states,
                start_date=start_date,
                end_date=end_date
            )
    
    def test_get_bulk_data_mixed_valid_invalid_states(self, service):
        """Test bulk data retrieval with mix of valid and invalid states."""
        start_date = datetime(2023, 12, 1)
        end_date = datetime(2023, 12, 31)
        states = ["CA", "INVALID", "NY"]
        
        with pytest.raises(ValueError, match="Invalid state codes"):
            service.get_bulk_data(
                states=states,
                start_date=start_date,
                end_date=end_date
            )
    
    def test_get_data_statistics_overview(self, service, sample_fiscal_data):
        """Test data statistics overview."""
        stats = service.get_data_statistics()
        
        assert "overview" in stats
        assert "by_state" in stats
        assert "data_quality" in stats
        assert "time_series" in stats
        
        overview = stats["overview"]
        assert "total_records" in overview
        assert "states_with_data" in overview
        assert "latest_timestamp" in overview
        assert "coverage_percentage" in overview
        
        assert overview["total_records"] >= 5  # Sample data count
        assert overview["states_with_data"] >= 3  # CA, NY, TX
        assert overview["coverage_percentage"] > 0
    
    def test_get_data_statistics_by_state(self, service, sample_fiscal_data):
        """Test data statistics by state."""
        stats = service.get_data_statistics()
        
        by_state = stats["by_state"]
        assert isinstance(by_state, list)
        
        # Should have stats for states with data
        state_codes = [state["state_code"] for state in by_state]
        assert "CA" in state_codes
        assert "NY" in state_codes
        assert "TX" in state_codes
        
        # Check state statistics format
        ca_stats = next(state for state in by_state if state["state_code"] == "CA")
        assert "record_count" in ca_stats
        assert "latest_timestamp" in ca_stats
        assert "date_range" in ca_stats
        assert ca_stats["record_count"] >= 3  # CA has 3 records in sample data
    
    def test_get_data_statistics_data_quality(self, service, sample_fiscal_data):
        """Test data quality statistics."""
        stats = service.get_data_statistics()
        
        data_quality = stats["data_quality"]
        assert "completeness" in data_quality
        assert "freshness" in data_quality
        assert "consistency" in data_quality
        
        # Completeness metrics
        completeness = data_quality["completeness"]
        assert "total_possible_records" in completeness
        assert "actual_records" in completeness
        assert "completeness_percentage" in completeness
        
        # Freshness metrics
        freshness = data_quality["freshness"]
        assert "most_recent_data" in freshness
        assert "days_since_last_update" in freshness
        
        # Consistency metrics
        consistency = data_quality["consistency"]
        assert "records_with_valid_values" in consistency
        assert "consistency_percentage" in consistency
    
    def test_format_record_for_export(self, service):
        """Test record formatting for export."""
        record = StateFiscalData(
            id=1,
            state_code="CA",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        formatted = service._format_record_for_export(record)
        
        assert "timestamp" in formatted
        assert "state" in formatted
        assert "state_tax_receipts_yoy_growth" in formatted
        assert "state_budget_surplus_deficit_as_pct_of_gsp" in formatted
        
        assert formatted["state"] == "CA"
        assert formatted["state_tax_receipts_yoy_growth"] == 3.5
        assert formatted["state_budget_surplus_deficit_as_pct_of_gsp"] == -1.2
        
        # Should include timestamp as ISO string
        assert isinstance(formatted["timestamp"], str)
        assert "2023-12-31" in formatted["timestamp"]
    
    def test_convert_to_response_model(self, service):
        """Test conversion to response model."""
        record = StateFiscalData(
            state_code="CA",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2
        )
        
        response = service._convert_to_response_model(record)
        
        assert isinstance(response, StateFiscalDataResponse)
        assert response.state == "CA"
        assert response.data_timestamp == datetime(2023, 12, 31)
        
        indicators = response.state_fiscal_indicators
        assert isinstance(indicators, StateFiscalIndicators)
        assert indicators.state_tax_receipts_yoy_growth == 3.5
        assert indicators.state_budget_surplus_deficit_as_pct_of_gsp == -1.2


class TestFiscalDataServiceErrorHandling:
    """Test error handling in fiscal data service."""
    
    def test_database_connection_error(self):
        """Test handling of database connection errors."""
        service = FiscalDataService()
        
        # Mock database manager that raises exception
        mock_db_manager = Mock()
        mock_db_manager.get_session_sync.side_effect = Exception("Database connection failed")
        service.db_manager = mock_db_manager
        
        with pytest.raises(Exception):
            service.get_latest_fiscal_data("CA", datetime.now())
    
    def test_invalid_date_range(self, service):
        """Test handling of invalid date ranges."""
        # End date before start date
        start_date = datetime(2023, 12, 31)
        end_date = datetime(2023, 1, 1)
        
        with pytest.raises(ValueError, match="Start date must be before end date"):
            service.get_historical_data("CA", start_date, end_date)
    
    def test_negative_limit_offset(self, service):
        """Test handling of negative limit and offset values."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        with pytest.raises(ValueError, match="Limit must be positive"):
            service.get_historical_data("CA", start_date, end_date, limit=-1)
        
        with pytest.raises(ValueError, match="Offset must be non-negative"):
            service.get_historical_data("CA", start_date, end_date, offset=-1)
    
    def test_excessive_limit(self, service):
        """Test handling of excessive limit values."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        # Should apply maximum limit
        result = service.get_historical_data("CA", start_date, end_date, limit=10000)
        
        # Should not raise error but apply reasonable limit
        assert isinstance(result, dict)


class TestFiscalDataServicePerformance:
    """Test performance-related aspects of fiscal data service."""
    
    def test_large_date_range_query(self, service, test_db_session):
        """Test query performance with large date ranges."""
        # Create test data spanning multiple years
        test_records = []
        for year in range(2020, 2024):
            for month in range(1, 13):
                record = StateFiscalData(
                    state_code="CA",
                    data_timestamp=datetime(year, month, 1),
                    state_tax_receipts_yoy_growth=3.5,
                    state_budget_surplus_deficit_as_pct_of_gsp=-1.2
                )
                test_records.append(record)
        
        test_db_session.add_all(test_records)
        test_db_session.commit()
        
        # Query large date range
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        result = service.get_historical_data("CA", start_date, end_date)
        
        assert result["record_count"] >= 48  # 4 years * 12 months
    
    def test_bulk_data_query_efficiency(self, service, test_db_session):
        """Test bulk data query efficiency."""
        # Create test data for multiple states
        states = ["CA", "NY", "TX", "FL", "IL"]
        test_records = []
        
        for state in states:
            for month in range(1, 13):
                record = StateFiscalData(
                    state_code=state,
                    data_timestamp=datetime(2023, month, 1),
                    state_tax_receipts_yoy_growth=3.5,
                    state_budget_surplus_deficit_as_pct_of_gsp=-1.2
                )
                test_records.append(record)
        
        test_db_session.add_all(test_records)
        test_db_session.commit()
        
        # Query bulk data
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        result = service.get_bulk_data(start_date=start_date, end_date=end_date)
        
        assert result["record_count"] >= 60  # 5 states * 12 months
        assert len(result["states"]) >= 5


class TestFiscalDataServiceValidation:
    """Test validation logic in fiscal data service."""
    
    def test_date_validation(self, service):
        """Test date parameter validation."""
        # Future dates should be handled gracefully
        future_date = datetime.now() + timedelta(days=365)
        
        result = service.get_latest_fiscal_data("CA", future_date)
        # Should return None or handle gracefully without error
        assert result is None or isinstance(result, StateFiscalDataResponse)
    
    def test_state_code_normalization(self, service):
        """Test state code normalization."""
        # Lowercase state codes should be handled
        with pytest.raises(ValueError):
            service._validate_state_code("ca")  # Should require uppercase
    
    def test_data_range_boundaries(self, service, sample_fiscal_data):
        """Test data retrieval at boundary conditions."""
        # Exact timestamp match
        exact_date = datetime(2023, 12, 31)
        result = service.get_latest_fiscal_data("CA", exact_date)
        assert result is not None
        assert result.data_timestamp == exact_date
        
        # Microsecond after
        after_date = datetime(2023, 12, 31, 0, 0, 0, 1)
        result = service.get_latest_fiscal_data("CA", after_date)
        assert result is not None
        assert result.data_timestamp == exact_date