"""
End-to-end tests for data flow through the system.
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime
import requests

from src.ingestion.data_service import StateFiscalDataService
from src.api.services.fiscal_service import FiscalDataService


class TestEndToEndDataFlow:
    """Test complete data flow from ingestion to API delivery."""
    
    @pytest.mark.asyncio
    async def test_complete_data_flow(self, test_db_session, test_client):
        """Test complete flow: ingestion -> storage -> API retrieval."""
        
        # Step 1: Mock external API data
        mock_indicators = {
            "state_tax_receipts_yoy_growth": 4.2,
            "state_budget_surplus_deficit_as_pct_of_gsp": -0.8
        }
        
        # Step 2: Ingest data using the ingestion service
        ingestion_service = StateFiscalDataService()
        ingestion_service.db_manager.get_session_sync = lambda: test_db_session
        
        with patch('src.ingestion.data_service.ExternalDataFetcher') as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch_all_state_data = AsyncMock(return_value=mock_indicators)
            mock_fetcher_class.return_value = mock_fetcher
            
            # Mock settings
            ingestion_service.settings.enable_data_validation = True
            ingestion_service.settings.enable_forward_fill = False
            
            target_date = datetime(2024, 1, 15)
            success = await ingestion_service.ingest_state_data("FL", target_date)
            assert success is True
        
        # Step 3: Verify data was stored correctly
        stored_data = ingestion_service.get_latest_data("FL", target_date)
        assert stored_data is not None
        assert stored_data.state_code == "FL"
        assert stored_data.state_tax_receipts_yoy_growth == 4.2
        assert stored_data.state_budget_surplus_deficit_as_pct_of_gsp == -0.8
        
        # Step 4: Retrieve data via API
        response = test_client.get("/api/v1/fiscal-data/FL?date=2024-01-15")
        assert response.status_code == 200
        
        api_data = response.json()
        assert api_data["state"] == "FL"
        assert api_data["state_fiscal_indicators"]["state_tax_receipts_yoy_growth"] == 4.2
        assert api_data["state_fiscal_indicators"]["state_budget_surplus_deficit_as_pct_of_gsp"] == -0.8
        
        # Step 5: Test historical data endpoint
        response = test_client.get("/api/v1/fiscal-data/FL/history")
        assert response.status_code == 200
        
        history_data = response.json()
        assert len(history_data["records"]) == 1
        assert history_data["records"][0]["state_tax_receipts_yoy_growth"] == 4.2
        
        # Step 6: Test bulk export
        response = test_client.get("/api/v1/fiscal-data/bulk?format=csv&states=FL")
        assert response.status_code == 200
        
        csv_content = response.content.decode()
        assert "FL" in csv_content
        assert "4.2" in csv_content
        assert "-0.8" in csv_content
    
    @pytest.mark.asyncio
    async def test_forward_fill_flow(self, test_db_session, test_client, sample_fiscal_data):
        """Test forward-fill functionality in complete flow."""
        
        # Step 1: Try to ingest data when external APIs are unavailable
        ingestion_service = StateFiscalDataService()
        ingestion_service.db_manager.get_session_sync = lambda: test_db_session
        
        with patch('src.ingestion.data_service.ExternalDataFetcher') as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch_all_state_data = AsyncMock(return_value=None)  # No external data
            mock_fetcher_class.return_value = mock_fetcher
            
            # Enable forward fill
            ingestion_service.settings.enable_forward_fill = True
            
            target_date = datetime(2024, 1, 15)
            success = await ingestion_service.ingest_state_data("CA", target_date)  # CA has historical data
            assert success is True
        
        # Step 2: Verify forward-filled data
        forward_filled = ingestion_service.get_latest_data("CA", target_date)
        assert forward_filled is not None
        assert forward_filled.data_timestamp == target_date
        
        # Values should match the latest historical data
        latest_historical = ingestion_service.get_latest_data("CA", datetime(2023, 12, 31))
        assert forward_filled.state_tax_receipts_yoy_growth == latest_historical.state_tax_receipts_yoy_growth
        assert forward_filled.state_budget_surplus_deficit_as_pct_of_gsp == latest_historical.state_budget_surplus_deficit_as_pct_of_gsp
        
        # Step 3: Retrieve via API
        response = test_client.get("/api/v1/fiscal-data/CA?date=2024-01-15")
        assert response.status_code == 200
        
        api_data = response.json()
        assert api_data["data_timestamp"].startswith("2024-01-15")
    
    @pytest.mark.asyncio
    async def test_data_validation_flow(self, test_db_session, test_client):
        """Test data validation in the ingestion flow."""
        
        # Step 1: Try to ingest invalid data
        invalid_indicators = {
            "state_tax_receipts_yoy_growth": "invalid",  # String instead of float
            "state_budget_surplus_deficit_as_pct_of_gsp": -1.2
        }
        
        ingestion_service = StateFiscalDataService()
        ingestion_service.db_manager.get_session_sync = lambda: test_db_session
        
        with patch('src.ingestion.data_service.ExternalDataFetcher') as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.fetch_all_state_data = AsyncMock(return_value=invalid_indicators)
            mock_fetcher_class.return_value = mock_fetcher
            
            # Enable validation
            ingestion_service.settings.enable_data_validation = True
            ingestion_service.settings.enable_forward_fill = False
            
            target_date = datetime(2024, 1, 15)
            success = await ingestion_service.ingest_state_data("FL", target_date)
            assert success is False  # Should fail validation
        
        # Step 2: Verify no data was stored
        stored_data = ingestion_service.get_latest_data("FL", target_date)
        assert stored_data is None
        
        # Step 3: Verify API returns 404
        response = test_client.get("/api/v1/fiscal-data/FL?date=2024-01-15")
        assert response.status_code == 404
    
    def test_comparative_analysis_flow(self, test_client, sample_fiscal_data):
        """Test comparative analysis across multiple states."""
        
        # Step 1: Get data for multiple states
        states_to_compare = ["CA", "NY", "TX"]
        state_data = {}
        
        for state in states_to_compare:
            response = test_client.get(f"/api/v1/fiscal-data/{state}")
            assert response.status_code == 200
            state_data[state] = response.json()
        
        # Step 2: Verify we have data for comparison
        assert len(state_data) == 3
        
        for state, data in state_data.items():
            assert data["state"] == state
            assert "state_fiscal_indicators" in data
            
            indicators = data["state_fiscal_indicators"]
            assert "state_tax_receipts_yoy_growth" in indicators
            assert "state_budget_surplus_deficit_as_pct_of_gsp" in indicators
        
        # Step 3: Test bulk export for comparison
        response = test_client.get(f"/api/v1/fiscal-data/bulk?format=json&states={','.join(states_to_compare)}")
        assert response.status_code == 200
        
        # Step 4: Verify comparative data structure
        for state in states_to_compare:
            state_response = test_client.get(f"/api/v1/fiscal-data/{state}/history?limit=5")
            assert state_response.status_code == 200
            
            history = state_response.json()
            assert history["state"] == state
            assert "records" in history
    
    def test_system_monitoring_flow(self, test_client, sample_fiscal_data):
        """Test system monitoring and health check flow."""
        
        # Step 1: Check basic health
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        
        # Step 2: Check detailed health
        response = test_client.get("/health/detailed")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "checks" in health_data
        assert "database" in health_data["checks"]
        
        # Step 3: Check metrics
        response = test_client.get("/metrics")
        assert response.status_code == 200
        
        metrics_content = response.text
        assert "state_fiscal_data_total_records" in metrics_content
        
        # Step 4: Check statistics
        response = test_client.get("/metrics/stats")
        assert response.status_code == 200
        
        stats = response.json()
        assert "overview" in stats
        assert stats["overview"]["total_records"] > 0
        
        # Step 5: Check data quality
        response = test_client.get("/metrics/data-quality")
        assert response.status_code == 200
        
        quality = response.json()
        assert "completeness" in quality
        assert "freshness" in quality
    
    def test_error_recovery_flow(self, test_client, sample_fiscal_data):
        """Test error handling and recovery scenarios."""
        
        # Step 1: Test invalid state code
        response = test_client.get("/api/v1/fiscal-data/INVALID")
        assert response.status_code == 400
        assert "Invalid state code" in response.json()["detail"]
        
        # Step 2: Test no data scenario
        response = test_client.get("/api/v1/fiscal-data/WY")  # Assuming WY has no test data
        assert response.status_code == 404
        assert "No fiscal data found" in response.json()["detail"]
        
        # Step 3: Test invalid date format (handled by FastAPI validation)
        response = test_client.get("/api/v1/fiscal-data/CA?date=invalid-date")
        assert response.status_code == 422  # Validation error
        
        # Step 4: Test invalid export format
        response = test_client.get("/api/v1/fiscal-data/bulk?format=invalid")
        assert response.status_code == 422  # Validation error
        
        # Step 5: Test invalid states in bulk export
        response = test_client.get("/api/v1/fiscal-data/bulk?states=INVALID")
        assert response.status_code == 400
        assert "Invalid state codes" in response.json()["detail"]
        
        # Step 6: Verify system remains healthy after errors
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    @pytest.mark.slow
    def test_performance_flow(self, test_client, sample_fiscal_data):
        """Test system performance with multiple requests."""
        import time
        
        # Step 1: Test concurrent requests for different states
        start_time = time.time()
        responses = []
        
        states_to_test = ["CA", "NY", "TX"]
        for state in states_to_test:
            response = test_client.get(f"/api/v1/fiscal-data/{state}")
            responses.append(response)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Step 2: Verify all responses are successful
        for response in responses:
            assert response.status_code == 200
        
        # Step 3: Check response times are reasonable (under 2 seconds total)
        assert total_time < 2.0
        
        # Step 4: Check that rate limiting headers are present
        for response in responses:
            assert "X-RateLimit-Limit" in response.headers
            assert "X-Process-Time" in response.headers
        
        # Step 5: Test bulk export performance
        start_time = time.time()
        response = test_client.get("/api/v1/fiscal-data/bulk?format=csv")
        end_time = time.time()
        
        assert response.status_code == 200
        bulk_time = end_time - start_time
        assert bulk_time < 5.0  # Bulk export should complete within 5 seconds