"""
Unit tests for data service.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from src.ingestion.data_service import StateFiscalDataService, DataValidationError
from src.shared.models import StateFiscalData


class TestStateFiscalDataService:
    """Test state fiscal data service."""
    
    @pytest.fixture
    def service(self, test_db_session):
        """Create service instance for testing."""
        service = StateFiscalDataService()
        # Mock the database manager to use test session
        service.db_manager.get_session_sync = lambda: test_db_session
        return service
    
    def test_data_exists(self, service, sample_fiscal_data):
        """Test checking if data exists."""
        target_date = datetime(2023, 12, 31)
        
        # Test existing data
        exists = service._data_exists("CA", target_date)
        assert exists is True
        
        # Test non-existing data
        exists = service._data_exists("WY", target_date)
        assert exists is False
        
        # Test different date
        exists = service._data_exists("CA", datetime(2024, 1, 1))
        assert exists is False
    
    def test_validate_indicators_valid(self, service):
        """Test validation of valid indicators."""
        indicators = {
            "state_tax_receipts_yoy_growth": 3.5,
            "state_budget_surplus_deficit_as_pct_of_gsp": -1.2
        }
        
        # Should not raise an exception
        service._validate_indicators(indicators, "CA", datetime.now())
    
    def test_validate_indicators_missing_field(self, service):
        """Test validation with missing required field."""
        indicators = {
            "state_tax_receipts_yoy_growth": 3.5
            # Missing budget field
        }
        
        with pytest.raises(DataValidationError, match="Missing required indicator"):
            service._validate_indicators(indicators, "CA", datetime.now())
    
    def test_validate_indicators_invalid_type(self, service):
        """Test validation with invalid data type."""
        indicators = {
            "state_tax_receipts_yoy_growth": "3.5",  # String instead of float
            "state_budget_surplus_deficit_as_pct_of_gsp": -1.2
        }
        
        with pytest.raises(DataValidationError, match="Invalid data type"):
            service._validate_indicators(indicators, "CA", datetime.now())
    
    def test_apply_forward_fill_success(self, service, sample_fiscal_data):
        """Test successful forward fill."""
        target_date = datetime(2024, 1, 1)  # Future date
        
        # Mock settings to enable forward fill
        service.settings.enable_forward_fill = True
        
        success = service._apply_forward_fill("CA", target_date)
        assert success is True
        
        # Verify the forward-filled record was created
        exists = service._data_exists("CA", target_date)
        assert exists is True
    
    def test_apply_forward_fill_no_historical_data(self, service):
        """Test forward fill with no historical data."""
        target_date = datetime(2024, 1, 1)
        
        success = service._apply_forward_fill("WY", target_date)  # State with no data
        assert success is False
    
    def test_apply_forward_fill_data_too_old(self, service, test_db_session):
        """Test forward fill with data that's too old."""
        # Create old data (more than 90 days ago)
        old_date = datetime.now() - timedelta(days=100)
        old_data = StateFiscalData(
            state_code="WY",
            data_timestamp=old_date,
            state_tax_receipts_yoy_growth=2.0,
            state_budget_surplus_deficit_as_pct_of_gsp=0.5
        )
        test_db_session.add(old_data)
        test_db_session.commit()
        
        target_date = datetime.now()
        success = service._apply_forward_fill("WY", target_date)
        assert success is False
    
    def test_get_latest_data(self, service, sample_fiscal_data):
        """Test getting latest data for a state."""
        before_date = datetime(2024, 1, 1)
        
        latest = service.get_latest_data("CA", before_date)
        assert latest is not None
        assert latest.state_code == "CA"
        assert latest.data_timestamp == datetime(2023, 12, 31)
        
        # Test with earlier date
        earlier_date = datetime(2023, 12, 1)
        latest = service.get_latest_data("CA", earlier_date)
        assert latest is not None
        assert latest.data_timestamp == datetime(2023, 11, 30)
        
        # Test with no data
        latest = service.get_latest_data("WY", before_date)
        assert latest is None
    
    def test_get_data_range(self, service, sample_fiscal_data):
        """Test getting data within a date range."""
        start_date = datetime(2023, 10, 1)
        end_date = datetime(2023, 12, 31)
        
        records = service.get_data_range("CA", start_date, end_date)
        assert len(records) == 3  # CA has 3 records in this range
        
        # Verify records are sorted by timestamp
        timestamps = [record.data_timestamp for record in records]
        assert timestamps == sorted(timestamps)
    
    def test_cleanup_old_data(self, service, test_db_session):
        """Test cleaning up old data."""
        # Create old data
        old_date = datetime.now() - timedelta(days=10)
        old_data = StateFiscalData(
            state_code="OLD",
            data_timestamp=old_date,
            state_tax_receipts_yoy_growth=1.0,
            state_budget_surplus_deficit_as_pct_of_gsp=0.0
        )
        test_db_session.add(old_data)
        test_db_session.commit()
        
        # Clean up with 5-day retention
        deleted_count = service.cleanup_old_data(retention_days=5)
        assert deleted_count >= 1
        
        # Verify old data was deleted
        remaining = test_db_session.query(StateFiscalData).filter(
            StateFiscalData.state_code == "OLD"
        ).first()
        assert remaining is None
    
    def test_get_ingestion_status(self, service, sample_fiscal_data):
        """Test getting ingestion status."""
        status = service.get_ingestion_status()
        
        assert "total_records" in status
        assert "state_counts" in status
        assert "latest_timestamp" in status
        assert "states_with_data" in status
        
        assert status["total_records"] >= 5  # We have sample data
        assert status["states_with_data"] >= 3  # CA, NY, TX
        assert status["latest_timestamp"] is not None
    
    @patch('src.ingestion.data_service.FreeDataFetcher')
    async def test_ingest_state_data_success(self, mock_fetcher_class, service):
        """Test successful state data ingestion."""
        # Mock the external data fetcher
        mock_fetcher = Mock()
        mock_fetcher.fetch_all_state_data = AsyncMock(return_value={
            "state_tax_receipts_yoy_growth": 3.5,
            "state_budget_surplus_deficit_as_pct_of_gsp": -1.2
        })
        mock_fetcher_class.return_value = mock_fetcher
        
        # Mock settings
        service.settings.enable_data_validation = True
        service.settings.enable_forward_fill = False
        
        target_date = datetime(2024, 1, 1)
        success = await service.ingest_state_data("FL", target_date)
        
        assert success is True
        
        # Verify data was stored
        exists = service._data_exists("FL", target_date)
        assert exists is True
    
    @patch('src.ingestion.data_service.FreeDataFetcher')
    async def test_ingest_state_data_no_external_data(self, mock_fetcher_class, service):
        """Test ingestion when no external data is available."""
        # Mock the external data fetcher to return None
        mock_fetcher = Mock()
        mock_fetcher.fetch_all_state_data = AsyncMock(return_value=None)
        mock_fetcher_class.return_value = mock_fetcher
        
        # Mock settings
        service.settings.enable_forward_fill = False
        
        target_date = datetime(2024, 1, 1)
        success = await service.ingest_state_data("FL", target_date)
        
        assert success is False
    
    @patch('src.ingestion.data_service.FreeDataFetcher')
    async def test_ingest_state_data_with_forward_fill(self, mock_fetcher_class, service, sample_fiscal_data):
        """Test ingestion with forward fill when external data is unavailable."""
        # Mock the external data fetcher to return None
        mock_fetcher = Mock()
        mock_fetcher.fetch_all_state_data = AsyncMock(return_value=None)
        mock_fetcher_class.return_value = mock_fetcher
        
        # Mock settings to enable forward fill
        service.settings.enable_forward_fill = True
        
        target_date = datetime(2024, 1, 1)
        success = await service.ingest_state_data("CA", target_date)  # CA has historical data
        
        assert success is True
        
        # Verify forward-filled data was stored
        exists = service._data_exists("CA", target_date)
        assert exists is True
    
    @patch('src.ingestion.data_service.FreeDataFetcher')
    async def test_ingest_all_states_data(self, mock_fetcher_class, service):
        """Test ingesting data for all states."""
        # Mock the external data fetcher
        mock_fetcher = Mock()
        mock_fetcher.fetch_all_state_data = AsyncMock(return_value={
            "state_tax_receipts_yoy_growth": 3.0,
            "state_budget_surplus_deficit_as_pct_of_gsp": 0.5
        })
        mock_fetcher_class.return_value = mock_fetcher
        
        # Mock settings
        service.settings.enable_data_validation = True
        service.settings.enable_forward_fill = False
        
        target_date = datetime(2024, 1, 1)
        
        # Test with a subset of states (to speed up test)
        with patch('src.shared.config.US_STATE_CODES', ["CA", "NY", "TX"]):
            results = await service.ingest_all_states_data(target_date)
        
        assert len(results) == 3
        assert all(results.values())  # All should be successful