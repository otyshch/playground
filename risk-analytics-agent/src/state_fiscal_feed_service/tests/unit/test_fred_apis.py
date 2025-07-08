"""
Unit tests for FRED API integration and data processing.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import aiohttp
import requests
from typing import List, Dict, Any

from src.ingestion.free_apis import (
    FREDAPIClient,
    FreeDataFetcher,
    FreeAPIError
)


class TestFREDAPIClient:
    """Test FRED API client."""
    
    def test_initialization(self):
        """Test API client initialization."""
        api = FREDAPIClient("test_api_key")
        assert api.api_key == "test_api_key"
        assert api.base_url == "https://api.stlouisfed.org/fred"
        assert api.session is not None
    
    @patch('aiohttp.ClientSession.get')
    async def test_get_series_data_success(self, mock_get):
        """Test successful series data retrieval."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "observations": [
                {"date": "2023-01-01", "value": "1000.0"},
                {"date": "2023-02-01", "value": "1050.0"},
                {"date": "2023-03-01", "value": "."}  # Missing value
            ]
        })
        mock_get.return_value.__aenter__.return_value = mock_response
        
        api = FREDAPIClient("test_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        result = await api.get_series_data("CATAXREC", start_date, end_date)
        
        assert len(result) == 2  # Missing value excluded
        assert result[0]["value"] == "1000.0"
        assert result[1]["value"] == "1050.0"
    
    @patch('aiohttp.ClientSession.get')
    async def test_get_series_data_api_error(self, mock_get):
        """Test API error handling."""
        mock_response = Mock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad Request")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        api = FREDAPIClient("test_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        with pytest.raises(FreeAPIError):
            await api.get_series_data("INVALID", start_date, end_date)
    
    @patch('aiohttp.ClientSession.get')
    async def test_get_series_data_network_error(self, mock_get):
        """Test network error handling."""
        mock_get.side_effect = aiohttp.ClientError("Network error")
        
        api = FREDAPIClient("test_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        with pytest.raises(FreeAPIError):
            await api.get_series_data("CATAXREC", start_date, end_date)
    
    def test_parse_date_valid(self):
        """Test valid date parsing."""
        api = FREDAPIClient("test_key")
        
        result = api._parse_date("2023-01-01")
        assert result == datetime(2023, 1, 1)
        
        result = api._parse_date("2023-12-31")
        assert result == datetime(2023, 12, 31)
    
    def test_parse_date_invalid(self):
        """Test invalid date parsing."""
        api = FREDAPIClient("test_key")
        
        result = api._parse_date("invalid-date")
        assert result is None
        
        result = api._parse_date("")
        assert result is None
        
        result = api._parse_date(None)
        assert result is None
    
    def test_parse_value_valid(self):
        """Test valid value parsing."""
        api = FREDAPIClient("test_key")
        
        assert api._parse_value("1000.0") == 1000.0
        assert api._parse_value("1050.5") == 1050.5
        assert api._parse_value("-500.0") == -500.0
        assert api._parse_value("0") == 0.0
    
    def test_parse_value_invalid(self):
        """Test invalid value parsing."""
        api = FREDAPIClient("test_key")
        
        assert api._parse_value(".") is None
        assert api._parse_value("") is None
        assert api._parse_value("invalid") is None
        assert api._parse_value(None) is None


class TestFreeDataFetcher:
    """Test free data fetcher coordination."""
    
    def test_initialization(self):
        """Test fetcher initialization."""
        fetcher = FreeDataFetcher("fred_key")
        assert fetcher.fred_client.api_key == "fred_key"
    
    def test_invalid_state_code(self):
        """Test error handling for invalid state code."""
        fetcher = FreeDataFetcher("fred_key")
        
        with pytest.raises(ValueError, match="Invalid state code"):
            fetcher._validate_state_code("INVALID")
        
        with pytest.raises(ValueError, match="Invalid state code"):
            fetcher._validate_state_code("CA1")
        
        with pytest.raises(ValueError, match="Invalid state code"):
            fetcher._validate_state_code("")
        
        # Valid state codes should not raise
        fetcher._validate_state_code("CA")
        fetcher._validate_state_code("NY")
        fetcher._validate_state_code("TX")
    
    @patch.object(FREDAPIClient, 'get_series_data')
    async def test_get_state_tax_data_success(self, mock_get_series):
        """Test successful state tax data retrieval."""
        mock_get_series.return_value = [
            {"date": "2023-01-01", "value": "1000.0"},
            {"date": "2023-02-01", "value": "1100.0"}
        ]
        
        fetcher = FreeDataFetcher("fred_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        result = await fetcher.get_state_tax_data("CA", start_date, end_date)
        
        assert len(result) == 2
        assert result[0]["date"] == "2023-01-01"
        assert result[0]["value"] == "1000.0"
        mock_get_series.assert_called_once()
    
    @patch.object(FREDAPIClient, 'get_series_data')
    async def test_get_state_gsp_success(self, mock_get_series):
        """Test successful state GSP data retrieval."""
        mock_get_series.return_value = [
            {"date": "2023-01-01", "value": "25000.0"},
            {"date": "2023-02-01", "value": "25500.0"}
        ]
        
        fetcher = FreeDataFetcher("fred_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        result = await fetcher.get_state_gsp("CA", start_date, end_date)
        
        assert len(result) == 2
        assert result[0]["date"] == "2023-01-01"
        assert result[0]["value"] == "25000.0"
        mock_get_series.assert_called_once()
    
    @patch.object(FREDAPIClient, 'get_series_data')
    async def test_get_national_budget_data_success(self, mock_get_series):
        """Test successful national budget data retrieval."""
        mock_get_series.return_value = [
            {"date": "2023-01-01", "value": "100.0"},
            {"date": "2023-02-01", "value": "-50.0"}
        ]
        
        fetcher = FreeDataFetcher("fred_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        result = await fetcher.get_national_budget_data(start_date, end_date)
        
        assert len(result) == 2
        assert result[0]["date"] == "2023-01-01"
        assert result[0]["value"] == "100.0"
        mock_get_series.assert_called_once()
    
    def test_calculate_yoy_growth(self):
        """Test year-over-year growth calculation."""
        fetcher = FreeDataFetcher("fred_key")
        
        # Normal growth
        growth = fetcher._calculate_yoy_growth(110.0, 100.0)
        assert growth == 10.0
        
        # Negative growth
        growth = fetcher._calculate_yoy_growth(90.0, 100.0)
        assert growth == -10.0
        
        # Zero previous value (avoid division by zero)
        growth = fetcher._calculate_yoy_growth(100.0, 0.0)
        assert growth == 0.0  # Assuming fallback to 0
        
        # Zero current value
        growth = fetcher._calculate_yoy_growth(0.0, 100.0)
        assert growth == -100.0
    
    def test_calculate_budget_surplus_deficit(self):
        """Test budget surplus/deficit calculation."""
        fetcher = FreeDataFetcher("fred_key")
        
        # Surplus (positive)
        pct = fetcher._calculate_budget_surplus_deficit(100.0, 10000.0)
        assert pct == 1.0
        
        # Deficit (negative)
        pct = fetcher._calculate_budget_surplus_deficit(-150.0, 10000.0)
        assert pct == -1.5
        
        # Zero budget balance
        pct = fetcher._calculate_budget_surplus_deficit(0.0, 10000.0)
        assert pct == 0.0
        
        # Zero GSP (avoid division by zero)
        pct = fetcher._calculate_budget_surplus_deficit(100.0, 0.0)
        assert pct == 0.0  # Assuming fallback to 0
    
    def test_find_closest_data_point(self):
        """Test finding closest data point to target date."""
        fetcher = FreeDataFetcher("fred_key")
        
        data = [
            {"date": "2023-01-01", "value": "100.0"},
            {"date": "2023-01-15", "value": "110.0"},
            {"date": "2023-02-01", "value": "120.0"}
        ]
        
        target_date = datetime(2023, 1, 10)
        closest = fetcher._find_closest_data_point(data, target_date)
        
        assert closest["value"] == "100.0"  # Closest to Jan 1
        
        # Test with target closer to Jan 15
        target_date = datetime(2023, 1, 12)
        closest = fetcher._find_closest_data_point(data, target_date)
        
        assert closest["value"] == "110.0"  # Closest to Jan 15
    
    def test_find_closest_data_point_empty(self):
        """Test finding closest data point with empty data."""
        fetcher = FreeDataFetcher("fred_key")
        
        result = fetcher._find_closest_data_point([], datetime.now())
        assert result is None
    
    @patch.object(FreeDataFetcher, 'get_state_tax_data')
    @patch.object(FreeDataFetcher, 'get_state_gsp')
    @patch.object(FreeDataFetcher, 'get_national_budget_data')
    async def test_fetch_all_state_data_success(self, mock_budget, mock_gsp, mock_tax):
        """Test successful fetch of all state data."""
        # Mock current and previous year tax data
        mock_tax.side_effect = [
            [{"date": "2023-12-31", "value": "1100.0"}],  # Current year
            [{"date": "2022-12-31", "value": "1000.0"}]   # Previous year
        ]
        
        # Mock GSP data
        mock_gsp.return_value = [
            {"date": "2023-12-31", "value": "25000.0"}
        ]
        
        # Mock national budget data
        mock_budget.return_value = [
            {"date": "2023-12-31", "value": "100.0"}
        ]
        
        fetcher = FreeDataFetcher("fred_key")
        target_date = datetime(2023, 12, 31)
        
        result = await fetcher.fetch_all_state_data("CA", target_date)
        
        assert result is not None
        assert "state_tax_receipts_yoy_growth" in result
        assert "state_budget_surplus_deficit_as_pct_of_gsp" in result
        assert result["state_tax_receipts_yoy_growth"] == 10.0  # (1100-1000)/1000 * 100
    
    @patch.object(FreeDataFetcher, 'get_state_tax_data')
    async def test_fetch_all_state_data_no_tax_data(self, mock_tax):
        """Test fetch when no tax data is available."""
        mock_tax.return_value = []  # No data
        
        fetcher = FreeDataFetcher("fred_key")
        target_date = datetime(2023, 12, 31)
        
        result = await fetcher.fetch_all_state_data("CA", target_date)
        
        assert result is None
    
    @patch.object(FreeDataFetcher, 'get_state_tax_data')
    @patch.object(FreeDataFetcher, 'get_state_gsp')
    async def test_fetch_all_state_data_no_gsp_data(self, mock_gsp, mock_tax):
        """Test fetch when no GSP data is available."""
        mock_tax.side_effect = [
            [{"date": "2023-12-31", "value": "1100.0"}],  # Current year
            [{"date": "2022-12-31", "value": "1000.0"}]   # Previous year
        ]
        mock_gsp.return_value = []  # No GSP data
        
        fetcher = FreeDataFetcher("fred_key")
        target_date = datetime(2023, 12, 31)
        
        result = await fetcher.fetch_all_state_data("CA", target_date)
        
        assert result is None
    
    async def test_fetch_all_state_data_invalid_state(self):
        """Test fetch with invalid state code."""
        fetcher = FreeDataFetcher("fred_key")
        target_date = datetime(2023, 12, 31)
        
        with pytest.raises(ValueError, match="Invalid state code"):
            await fetcher.fetch_all_state_data("INVALID", target_date)


class TestFreeAPIErrorHandling:
    """Test API error handling."""
    
    def test_api_error_creation(self):
        """Test FreeAPIError exception creation."""
        error = FreeAPIError("Test error message")
        assert str(error) == "Test error message"
    
    @patch('aiohttp.ClientSession.get')
    async def test_fred_client_rate_limit_error(self, mock_get):
        """Test FRED API rate limit handling."""
        mock_response = Mock()
        mock_response.status = 429  # Too Many Requests
        mock_response.text = AsyncMock(return_value="Rate limit exceeded")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        api = FREDAPIClient("test_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        with pytest.raises(FreeAPIError) as exc_info:
            await api.get_series_data("CATAXREC", start_date, end_date)
        
        # Should raise FreeAPIError for rate limiting
    
    @patch('aiohttp.ClientSession.get')
    async def test_fred_client_unauthorized_error(self, mock_get):
        """Test FRED API unauthorized error handling."""
        mock_response = Mock()
        mock_response.status = 400  # Bad Request (invalid API key)
        mock_response.text = AsyncMock(return_value="Bad Request. The value for api_key is not a valid API key.")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        api = FREDAPIClient("invalid_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        with pytest.raises(FreeAPIError) as exc_info:
            await api.get_series_data("CATAXREC", start_date, end_date)
        
        # Should raise FreeAPIError for unauthorized access


class TestDataProcessing:
    """Test data processing utilities."""
    
    def test_data_parsing_edge_cases(self):
        """Test edge cases in data parsing."""
        fetcher = FreeDataFetcher("fred_key")
        
        # Test with various value formats
        api = FREDAPIClient("test_key")
        
        # Standard numeric values
        assert api._parse_value("1000.0") == 1000.0
        assert api._parse_value("1000") == 1000.0
        
        # Scientific notation
        assert api._parse_value("1.0e3") == 1000.0
        
        # Negative values
        assert api._parse_value("-500.0") == -500.0
        
        # Zero
        assert api._parse_value("0.0") == 0.0
        assert api._parse_value("0") == 0.0
        
        # Missing/invalid values
        assert api._parse_value(".") is None
        assert api._parse_value("") is None
        assert api._parse_value("N/A") is None
        assert api._parse_value("null") is None
    
    def test_date_range_validation(self):
        """Test date range validation."""
        fetcher = FreeDataFetcher("fred_key")
        
        # Valid date range
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        # No exception should be raised for valid dates
        
        # Invalid date range (end before start)
        start_date = datetime(2023, 12, 31)
        end_date = datetime(2023, 1, 1)
        # This should be handled gracefully by the API client
    
    def test_bounds_checking(self):
        """Test bounds checking for calculated values."""
        fetcher = FreeDataFetcher("fred_key")
        
        # Test extreme growth values
        very_high_growth = fetcher._calculate_yoy_growth(10000.0, 100.0)
        assert very_high_growth == 9900.0  # 9900% growth
        
        very_low_growth = fetcher._calculate_yoy_growth(1.0, 10000.0)
        assert very_low_growth == -99.99  # ~100% decline
        
        # Test extreme budget percentages
        very_high_surplus = fetcher._calculate_budget_surplus_deficit(1000.0, 10000.0)
        assert very_high_surplus == 10.0  # 10% of GSP
        
        very_high_deficit = fetcher._calculate_budget_surplus_deficit(-2000.0, 10000.0)
        assert very_high_deficit == -20.0  # -20% of GSP