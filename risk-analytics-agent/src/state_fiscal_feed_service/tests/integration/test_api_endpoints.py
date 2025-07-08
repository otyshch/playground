"""
Integration tests for API endpoints.
"""
import pytest
from datetime import datetime
import json

from src.shared.config import US_STATE_CODES


class TestFiscalDataEndpoints:
    """Test fiscal data API endpoints."""
    
    def test_get_fiscal_data_valid_state(self, test_client, sample_fiscal_data):
        """Test getting fiscal data for a valid state."""
        response = test_client.get("/api/v1/fiscal-data/CA")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "data_timestamp" in data
        assert data["state"] == "CA"
        assert "state_fiscal_indicators" in data
        assert "state_tax_receipts_yoy_growth" in data["state_fiscal_indicators"]
        assert "state_budget_surplus_deficit_as_pct_of_gsp" in data["state_fiscal_indicators"]
    
    def test_get_fiscal_data_with_date(self, test_client, sample_fiscal_data):
        """Test getting fiscal data with specific date."""
        response = test_client.get("/api/v1/fiscal-data/CA?date=2023-12-31")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["state"] == "CA"
        assert data["data_timestamp"].startswith("2023-12-31")
    
    def test_get_fiscal_data_invalid_state(self, test_client):
        """Test getting fiscal data for invalid state."""
        response = test_client.get("/api/v1/fiscal-data/INVALID")
        
        assert response.status_code == 400
        assert "Invalid state code" in response.json()["detail"]
    
    def test_get_fiscal_data_no_data(self, test_client):
        """Test getting fiscal data when no data exists."""
        response = test_client.get("/api/v1/fiscal-data/WY")
        
        assert response.status_code == 404
        assert "No fiscal data found" in response.json()["detail"]
    
    def test_get_state_history(self, test_client, sample_fiscal_data):
        """Test getting historical data for a state."""
        response = test_client.get("/api/v1/fiscal-data/CA/history")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["state"] == "CA"
        assert "records" in data
        assert len(data["records"]) > 0
        assert "record_count" in data
    
    def test_get_state_history_with_date_range(self, test_client, sample_fiscal_data):
        """Test getting historical data with date range."""
        response = test_client.get(
            "/api/v1/fiscal-data/CA/history"
            "?start_date=2023-11-01&end_date=2023-12-31"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["state"] == "CA"
        assert len(data["records"]) >= 2  # CA has data in this range
    
    def test_get_state_history_with_limit(self, test_client, sample_fiscal_data):
        """Test getting historical data with limit."""
        response = test_client.get("/api/v1/fiscal-data/CA/history?limit=1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["records"]) == 1
    
    def test_bulk_export_csv(self, test_client, sample_fiscal_data):
        """Test bulk data export in CSV format."""
        response = test_client.get("/api/v1/fiscal-data/bulk?format=csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        
        # Check CSV content
        content = response.content.decode()
        lines = content.strip().split('\n')
        
        # Should have header
        header = lines[0]
        assert "timestamp" in header
        assert "state" in header
        assert "state_tax_receipts_yoy_growth" in header
        assert "state_budget_surplus_deficit_as_pct_of_gsp" in header
        
        # Should have data rows
        assert len(lines) > 1
    
    def test_bulk_export_json(self, test_client, sample_fiscal_data):
        """Test bulk data export in JSON format."""
        response = test_client.get("/api/v1/fiscal-data/bulk?format=json")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]
    
    def test_bulk_export_with_filters(self, test_client, sample_fiscal_data):
        """Test bulk export with state and date filters."""
        response = test_client.get(
            "/api/v1/fiscal-data/bulk"
            "?format=csv&states=CA,NY&start_date=2023-12-01&end_date=2023-12-31"
        )
        
        assert response.status_code == 200
        
        # Check that only CA and NY data is included
        content = response.content.decode()
        lines = content.strip().split('\n')
        
        # Check data rows (skip header)
        for line in lines[1:]:
            if line.strip():  # Skip empty lines
                state = line.split(',')[1]  # State is second column
                assert state in ["CA", "NY"]
    
    def test_bulk_export_invalid_states(self, test_client):
        """Test bulk export with invalid state codes."""
        response = test_client.get("/api/v1/fiscal-data/bulk?states=INVALID,ALSO_INVALID")
        
        assert response.status_code == 400
        assert "Invalid state codes" in response.json()["detail"]
    
    def test_list_states(self, test_client):
        """Test listing available states."""
        response = test_client.get("/api/v1/fiscal-data/states")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "states" in data
        assert "total_count" in data
        assert data["total_count"] == len(US_STATE_CODES)
        
        # Check first state entry format
        first_state = data["states"][0]
        assert "code" in first_state
        assert "name" in first_state
        assert len(first_state["code"]) == 2


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_basic_health_check(self, test_client):
        """Test basic health check."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "State Fiscal Data Feed API"
    
    def test_detailed_health_check(self, test_client):
        """Test detailed health check."""
        response = test_client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "configuration" in data["checks"]
    
    def test_readiness_check(self, test_client):
        """Test readiness probe."""
        response = test_client.get("/health/readiness")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ready"
        assert "timestamp" in data
    
    def test_liveness_check(self, test_client):
        """Test liveness probe."""
        response = test_client.get("/health/liveness")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "alive"
        assert "timestamp" in data


class TestMetricsEndpoints:
    """Test metrics endpoints."""
    
    def test_prometheus_metrics(self, test_client, sample_fiscal_data):
        """Test Prometheus metrics endpoint."""
        response = test_client.get("/metrics")
        
        assert response.status_code == 200
        content = response.text
        
        # Check for expected metrics
        assert "state_fiscal_data_total_records" in content
        assert "state_fiscal_data_states_count" in content
        assert "state_fiscal_data_records_by_state" in content
    
    def test_detailed_statistics(self, test_client, sample_fiscal_data):
        """Test detailed statistics endpoint."""
        response = test_client.get("/metrics/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "overview" in data
        assert "by_state" in data
        assert "data_quality" in data
        assert "time_series" in data
        
        # Check overview section
        overview = data["overview"]
        assert "total_records" in overview
        assert "states_with_data" in overview
        assert "coverage_percentage" in overview
    
    def test_data_quality_metrics(self, test_client, sample_fiscal_data):
        """Test data quality metrics endpoint."""
        response = test_client.get("/metrics/data-quality")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "completeness" in data
        assert "freshness" in data
        assert "consistency" in data


class TestAPIErrorHandling:
    """Test API error handling."""
    
    def test_404_endpoint(self, test_client):
        """Test 404 for non-existent endpoint."""
        response = test_client.get("/non-existent-endpoint")
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, test_client):
        """Test 405 for unsupported HTTP method."""
        response = test_client.post("/api/v1/fiscal-data/CA")
        
        assert response.status_code == 405
    
    def test_validation_error(self, test_client):
        """Test validation error handling."""
        response = test_client.get("/api/v1/fiscal-data/CA/history?limit=invalid")
        
        assert response.status_code == 422  # Validation error


class TestCORSHeaders:
    """Test CORS headers."""
    
    def test_cors_headers(self, test_client):
        """Test that CORS headers are present."""
        response = test_client.get("/api/v1/fiscal-data/states")
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
    
    def test_options_request(self, test_client):
        """Test OPTIONS request for CORS preflight."""
        response = test_client.options("/api/v1/fiscal-data/states")
        
        assert response.status_code == 200
        assert "access-control-allow-methods" in response.headers


class TestRateLimiting:
    """Test rate limiting middleware."""
    
    def test_rate_limit_headers(self, test_client):
        """Test that rate limit headers are present."""
        response = test_client.get("/api/v1/fiscal-data/states")
        
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
    
    def test_correlation_id_header(self, test_client):
        """Test that correlation ID header is present."""
        response = test_client.get("/api/v1/fiscal-data/states")
        
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        assert "X-Process-Time" in response.headers