"""
End-to-end tests for complete workflow scenarios.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import json
import asyncio

from src.ingestion.data_service import StateFiscalDataService
from src.ingestion.free_apis import FreeDataFetcher
from src.shared.models import StateFiscalData


class TestCompleteDataIngestionWorkflow:
    """Test complete data ingestion workflow from API to database."""
    
    @patch.object(FreeDataFetcher, 'fetch_all_state_data')
    async def test_complete_ingestion_workflow(self, mock_fetch, test_db_session):
        """Test complete workflow from external API to database storage."""
        # Mock external API response
        mock_fetch.return_value = {
            "state_tax_receipts_yoy_growth": 4.2,
            "state_budget_surplus_deficit_as_pct_of_gsp": -1.8
        }
        
        # Create data service
        service = StateFiscalDataService()
        service.db_manager.get_session_sync = lambda: test_db_session
        
        target_date = datetime(2024, 1, 1)
        state_code = "CA"
        
        # Perform ingestion
        success = await service.ingest_state_data(state_code, target_date)
        
        assert success is True
        
        # Verify data was stored in database
        stored_record = test_db_session.query(StateFiscalData).filter(
            StateFiscalData.state_code == state_code,
            StateFiscalData.data_timestamp == target_date
        ).first()
        
        assert stored_record is not None
        assert stored_record.state_tax_receipts_yoy_growth == 4.2
        assert stored_record.state_budget_surplus_deficit_as_pct_of_gsp == -1.8
        assert stored_record.created_at is not None
        assert stored_record.updated_at is not None
    
    @patch.object(FreeDataFetcher, 'fetch_all_state_data')
    async def test_bulk_state_ingestion_workflow(self, mock_fetch, test_db_session):
        """Test bulk ingestion workflow for multiple states."""
        # Mock external API response
        mock_fetch.return_value = {
            "state_tax_receipts_yoy_growth": 3.0,
            "state_budget_surplus_deficit_as_pct_of_gsp": 0.5
        }
        
        # Create data service
        service = StateFiscalDataService()
        service.db_manager.get_session_sync = lambda: test_db_session
        
        target_date = datetime(2024, 1, 1)
        test_states = ["CA", "NY", "TX"]
        
        # Mock US_STATE_CODES to limit test scope
        with patch('src.shared.config.US_STATE_CODES', test_states):
            results = await service.ingest_all_states_data(target_date)
        
        # Verify all states were processed successfully
        assert len(results) == len(test_states)
        assert all(results.values())
        
        # Verify data was stored for all states
        for state_code in test_states:
            stored_record = test_db_session.query(StateFiscalData).filter(
                StateFiscalData.state_code == state_code,
                StateFiscalData.data_timestamp == target_date
            ).first()
            
            assert stored_record is not None
            assert stored_record.state_tax_receipts_yoy_growth == 3.0
    
    async def test_ingestion_with_api_failure_and_forward_fill(self, test_db_session, sample_fiscal_data):
        """Test ingestion workflow when API fails but forward fill succeeds."""
        # Create data service
        service = StateFiscalDataService()
        service.db_manager.get_session_sync = lambda: test_db_session
        service.settings.enable_forward_fill = True
        
        # Mock API failure
        with patch.object(FreeDataFetcher, 'fetch_all_state_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None  # API failure
            
            target_date = datetime(2024, 1, 1)  # Future date for forward fill
            success = await service.ingest_state_data("CA", target_date)
        
        assert success is True
        
        # Verify forward-filled data was stored
        stored_record = test_db_session.query(StateFiscalData).filter(
            StateFiscalData.state_code == "CA",
            StateFiscalData.data_timestamp == target_date
        ).first()
        
        assert stored_record is not None
        # Should have values from most recent historical data
        assert stored_record.state_tax_receipts_yoy_growth == 3.5  # From sample data
    
    async def test_ingestion_failure_no_fallback(self, test_db_session):
        """Test ingestion workflow when both API and forward fill fail."""
        # Create data service
        service = StateFiscalDataService()
        service.db_manager.get_session_sync = lambda: test_db_session
        service.settings.enable_forward_fill = False
        
        # Mock API failure
        with patch.object(FreeDataFetcher, 'fetch_all_state_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None  # API failure
            
            target_date = datetime(2024, 1, 1)
            success = await service.ingest_state_data("WY", target_date)  # State with no historical data
        
        assert success is False
        
        # Verify no data was stored
        stored_record = test_db_session.query(StateFiscalData).filter(
            StateFiscalData.state_code == "WY",
            StateFiscalData.data_timestamp == target_date
        ).first()
        
        assert stored_record is None


class TestCompleteAPIWorkflow:
    """Test complete API workflow from request to response."""
    
    def test_complete_api_retrieval_workflow(self, test_client, sample_fiscal_data):
        """Test complete workflow for API data retrieval."""
        # Test single state data retrieval
        response = test_client.get("/api/v1/fiscal-data/CA")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "data_timestamp" in data
        assert "state" in data
        assert "state_fiscal_indicators" in data
        
        # Verify data content
        assert data["state"] == "CA"
        indicators = data["state_fiscal_indicators"]
        assert "state_tax_receipts_yoy_growth" in indicators
        assert "state_budget_surplus_deficit_as_pct_of_gsp" in indicators
    
    def test_complete_historical_data_workflow(self, test_client, sample_fiscal_data):
        """Test complete workflow for historical data retrieval."""
        # Test historical data retrieval with date range
        response = test_client.get(
            "/api/v1/fiscal-data/CA/history"
            "?start_date=2023-10-01&end_date=2023-12-31&limit=10"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "state" in data
        assert "records" in data
        assert "record_count" in data
        assert "date_range" in data
        
        # Verify data content
        assert data["state"] == "CA"
        assert data["record_count"] >= 3  # CA has 3 records in this range
        assert len(data["records"]) >= 3
        
        # Verify records are properly formatted
        for record in data["records"]:
            assert "data_timestamp" in record
            assert "state_fiscal_indicators" in record
    
    def test_complete_bulk_export_workflow(self, test_client, sample_fiscal_data):
        """Test complete workflow for bulk data export."""
        # Test CSV export
        response = test_client.get(
            "/api/v1/fiscal-data/bulk"
            "?format=csv&states=CA,NY,TX&start_date=2023-12-01&end_date=2023-12-31"
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        # Verify CSV content
        content = response.content.decode()
        lines = content.strip().split('\n')
        
        # Should have header and data rows
        assert len(lines) >= 4  # Header + 3 states
        
        # Verify header
        header = lines[0]
        assert "timestamp" in header
        assert "state" in header
        assert "state_tax_receipts_yoy_growth" in header
        assert "state_budget_surplus_deficit_as_pct_of_gsp" in header
        
        # Test JSON export
        response = test_client.get(
            "/api/v1/fiscal-data/bulk"
            "?format=json&states=CA,NY&start_date=2023-12-01&end_date=2023-12-31"
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert "records" in data
        assert "record_count" in data
        assert data["record_count"] >= 2  # CA and NY
    
    def test_complete_api_error_handling_workflow(self, test_client):
        """Test complete workflow for API error handling."""
        # Test invalid state code
        response = test_client.get("/api/v1/fiscal-data/INVALID")
        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data
        assert "Invalid state code" in error_data["detail"]
        
        # Test not found scenario
        response = test_client.get("/api/v1/fiscal-data/WY")
        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        assert "No fiscal data found" in error_data["detail"]
        
        # Test validation error
        response = test_client.get("/api/v1/fiscal-data/CA/history?limit=invalid")
        assert response.status_code == 422  # Validation error


class TestCompleteMonitoringWorkflow:
    """Test complete monitoring and health check workflow."""
    
    def test_complete_health_check_workflow(self, test_client):
        """Test complete health check workflow."""
        # Basic health check
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        
        # Detailed health check
        response = test_client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]
        
        # Readiness probe
        response = test_client.get("/health/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        
        # Liveness probe
        response = test_client.get("/health/liveness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
    
    def test_complete_metrics_workflow(self, test_client, sample_fiscal_data):
        """Test complete metrics and monitoring workflow."""
        # Prometheus metrics
        response = test_client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Should contain expected metrics
        assert "state_fiscal_data_total_records" in content
        assert "state_fiscal_data_states_count" in content
        
        # Detailed statistics
        response = test_client.get("/metrics/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "overview" in data
        assert "by_state" in data
        assert "data_quality" in data
        
        # Data quality metrics
        response = test_client.get("/metrics/data-quality")
        assert response.status_code == 200
        data = response.json()
        
        assert "completeness" in data
        assert "freshness" in data
        assert "consistency" in data


class TestCompleteDataValidationWorkflow:
    """Test complete data validation workflow."""
    
    @patch.object(FreeDataFetcher, 'fetch_all_state_data')
    async def test_data_validation_workflow(self, mock_fetch, test_db_session):
        """Test complete data validation workflow."""
        # Mock API response with edge case values
        mock_fetch.return_value = {
            "state_tax_receipts_yoy_growth": 150.0,  # High growth
            "state_budget_surplus_deficit_as_pct_of_gsp": -25.0  # Large deficit
        }
        
        # Create data service with validation enabled
        service = StateFiscalDataService()
        service.db_manager.get_session_sync = lambda: test_db_session
        service.settings.enable_data_validation = True
        
        target_date = datetime(2024, 1, 1)
        state_code = "CA"
        
        # Perform ingestion
        success = await service.ingest_state_data(state_code, target_date)
        
        # Should succeed even with edge case values
        assert success is True
        
        # Verify data was stored
        stored_record = test_db_session.query(StateFiscalData).filter(
            StateFiscalData.state_code == state_code,
            StateFiscalData.data_timestamp == target_date
        ).first()
        
        assert stored_record is not None
        # Values should be stored as-is (validation doesn't modify values)
        assert stored_record.state_tax_receipts_yoy_growth == 150.0
        assert stored_record.state_budget_surplus_deficit_as_pct_of_gsp == -25.0
    
    @patch.object(FreeDataFetcher, 'fetch_all_state_data')
    async def test_data_validation_failure_workflow(self, mock_fetch, test_db_session):
        """Test data validation failure workflow."""
        # Mock API response with invalid data structure
        mock_fetch.return_value = {
            "invalid_field": 3.5,
            # Missing required fields
        }
        
        # Create data service with validation enabled
        service = StateFiscalDataService()
        service.db_manager.get_session_sync = lambda: test_db_session
        service.settings.enable_data_validation = True
        
        target_date = datetime(2024, 1, 1)
        state_code = "CA"
        
        # Perform ingestion - should fail validation
        success = await service.ingest_state_data(state_code, target_date)
        
        # Should fail due to validation error
        assert success is False
        
        # Verify no data was stored
        stored_record = test_db_session.query(StateFiscalData).filter(
            StateFiscalData.state_code == state_code,
            StateFiscalData.data_timestamp == target_date
        ).first()
        
        assert stored_record is None


class TestCompleteErrorRecoveryWorkflow:
    """Test complete error recovery workflow."""
    
    async def test_database_recovery_workflow(self, test_db_session):
        """Test database error recovery workflow."""
        service = StateFiscalDataService()
        
        # Mock database manager that fails first, then succeeds
        call_count = 0
        def mock_get_session():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Database connection failed")
            return test_db_session
        
        service.db_manager.get_session_sync = mock_get_session
        
        # First attempt should fail
        with pytest.raises(Exception):
            await service.ingest_state_data("CA", datetime.now())
        
        # Mock successful API response for retry
        with patch.object(FreeDataFetcher, 'fetch_all_state_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "state_tax_receipts_yoy_growth": 3.5,
                "state_budget_surplus_deficit_as_pct_of_gsp": -1.2
            }
            
            # Second attempt should succeed
            success = await service.ingest_state_data("CA", datetime.now())
            assert success is True
    
    def test_api_rate_limit_recovery_workflow(self, test_client):
        """Test API rate limit recovery workflow."""
        # This test would require implementing rate limiting
        # and testing recovery mechanisms
        
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = test_client.get("/api/v1/fiscal-data/states")
            responses.append(response.status_code)
        
        # All requests should succeed in test environment
        # In production, rate limiting would be applied
        assert all(status == 200 for status in responses)


class TestCompletePerformanceWorkflow:
    """Test complete performance workflow scenarios."""
    
    def test_large_dataset_workflow(self, test_client, test_db_session):
        """Test workflow with large datasets."""
        # Create large test dataset
        test_records = []
        states = ["CA", "NY", "TX", "FL", "IL"]
        
        for state in states:
            for year in range(2020, 2024):
                for month in range(1, 13):
                    record = StateFiscalData(
                        state_code=state,
                        data_timestamp=datetime(year, month, 1),
                        state_tax_receipts_yoy_growth=3.5,
                        state_budget_surplus_deficit_as_pct_of_gsp=-1.2
                    )
                    test_records.append(record)
        
        test_db_session.add_all(test_records)
        test_db_session.commit()
        
        # Test bulk export performance
        response = test_client.get(
            "/api/v1/fiscal-data/bulk"
            "?format=json&start_date=2020-01-01&end_date=2023-12-31"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle large dataset efficiently
        assert data["record_count"] >= 240  # 5 states * 4 years * 12 months
        assert len(data["records"]) == data["record_count"]
    
    def test_concurrent_request_workflow(self, test_client, sample_fiscal_data):
        """Test workflow with concurrent requests."""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                response = test_client.get("/api/v1/fiscal-data/CA")
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(errors) == 0
        assert all(status == 200 for status in results)
        assert len(results) == 10