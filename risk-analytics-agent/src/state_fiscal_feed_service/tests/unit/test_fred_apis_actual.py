"""
Unit tests for FRED API integration - Updated to match actual implementation.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
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
    
    @patch('requests.Session.get')
    def test_get_state_tax_collections_success(self, mock_get):
        """Test successful state tax collections retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "observations": [
                {"date": "2023-01-01", "value": "1000.0"},
                {"date": "2023-02-01", "value": "1050.0"},
                {"date": "2023-03-01", "value": "."}  # Missing value
            ]
        }
        mock_get.return_value = mock_response
        
        api = FREDAPIClient("test_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        result = api.get_state_tax_collections("CA", start_date, end_date)
        
        assert len(result) == 2  # Missing value excluded
        assert result[0]["value"] == 1000.0
        assert result[1]["value"] == 1050.0
    
    @patch('requests.Session.get')
    def test_get_state_tax_collections_api_error(self, mock_get):
        """Test API error handling."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Bad Request")
        mock_get.return_value = mock_response
        
        api = FREDAPIClient("test_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        result = api.get_state_tax_collections("INVALID", start_date, end_date)
        assert result == []  # Returns empty list on error
    
    @patch('requests.Session.get')
    def test_get_state_gsp_success(self, mock_get):
        """Test successful state GSP data retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "observations": [
                {"date": "2023-01-01", "value": "25000.0"},
                {"date": "2023-02-01", "value": "25500.0"}
            ]
        }
        mock_get.return_value = mock_response
        
        api = FREDAPIClient("test_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        result = api.get_state_gsp("CA", start_date, end_date)
        
        assert len(result) == 2
        assert result[0]["value"] == 25000.0
        assert result[1]["value"] == 25500.0
    
    @patch('requests.Session.get')
    def test_get_national_budget_balance_success(self, mock_get):
        """Test successful national budget data retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "observations": [
                {"date": "2023-01-01", "value": "100.0"},
                {"date": "2023-02-01", "value": "-50.0"}
            ]
        }
        mock_get.return_value = mock_response
        
        api = FREDAPIClient("test_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        result = api.get_national_budget_balance(start_date, end_date)
        
        assert len(result) == 2
        assert result[0]["value"] == 100.0
        assert result[1]["value"] == -50.0


class TestFreeDataFetcher:
    """Test free data fetcher coordination."""
    
    def test_initialization(self):
        """Test fetcher initialization."""
        fetcher = FreeDataFetcher("fred_key")
        assert fetcher.fred_client.api_key == "fred_key"
    
    def test_initialization_without_key(self):
        """Test fetcher initialization without API key."""
        fetcher = FreeDataFetcher()
        assert fetcher.fred_client is None
    
    @patch.object(FREDAPIClient, 'get_state_tax_collections')
    @patch.object(FREDAPIClient, 'get_state_gsp')
    @patch.object(FREDAPIClient, 'get_national_budget_balance')
    @patch.object(FREDAPIClient, 'get_national_tax_totals')
    def test_fetch_state_fiscal_data_success(self, mock_tax_totals, mock_budget, mock_gsp, mock_tax):
        """Test successful fetch of state fiscal data."""
        # Mock responses
        mock_tax.return_value = [
            {"date": datetime(2023, 12, 31), "value": 1100.0}
        ]
        mock_gsp.return_value = [
            {"date": datetime(2023, 12, 31), "value": 25000.0}
        ]
        mock_budget.return_value = [
            {"date": datetime(2023, 12, 31), "value": 100.0}
        ]
        mock_tax_totals.return_value = [
            {"date": datetime(2023, 12, 31), "value": 50000.0}
        ]
        
        fetcher = FreeDataFetcher("fred_key")
        target_date = datetime(2023, 12, 31)
        
        result = fetcher.fetch_state_fiscal_data("CA", target_date)
        
        assert result is not None
        assert result["state_code"] == "CA"
        assert result["target_date"] == target_date
        assert len(result["tax_receipts_data"]) == 1
        assert len(result["gsp_data"]) == 1
    
    def test_fetch_state_fiscal_data_no_fred_client(self):
        """Test fetch when no FRED client is available."""
        fetcher = FreeDataFetcher()  # No API key
        target_date = datetime(2023, 12, 31)
        
        result = fetcher.fetch_state_fiscal_data("CA", target_date)
        
        assert result is not None
        assert result["state_code"] == "CA"
        assert result["tax_receipts_data"] == []
        assert result["gsp_data"] == []
    
    def test_calculate_fiscal_indicators_with_sufficient_data(self):
        """Test fiscal indicators calculation with sufficient data."""
        fetcher = FreeDataFetcher("fred_key")
        
        # Mock fiscal data with sufficient tax data for YoY calculation
        fiscal_data = {
            'state_code': 'CA',
            'tax_receipts_data': [
                {'date': datetime(2022, 12, 31), 'value': 1000.0},  # 5 quarters ago
                {'date': datetime(2023, 3, 31), 'value': 1020.0},   # 4 quarters ago
                {'date': datetime(2023, 6, 30), 'value': 1040.0},   # 3 quarters ago
                {'date': datetime(2023, 9, 30), 'value': 1060.0},   # 2 quarters ago
                {'date': datetime(2023, 12, 31), 'value': 1100.0}   # Latest
            ],
            'gsp_data': [
                {'date': datetime(2023, 12, 31), 'value': 25000.0}
            ],
            'national_budget_data': [
                {'date': datetime(2023, 12, 31), 'value': 500.0}
            ],
            'national_tax_data': [
                {'date': datetime(2023, 12, 31), 'value': 50000.0}
            ]
        }
        
        result = fetcher.calculate_fiscal_indicators(fiscal_data)
        
        assert result is not None
        assert 'state_tax_receipts_yoy_growth' in result
        assert 'state_budget_surplus_deficit_as_pct_of_gsp' in result
        
        # YoY growth should be calculated: (1100 - 1020) / 1020 * 100 ≈ 7.84%
        assert result['state_tax_receipts_yoy_growth'] is not None
        assert isinstance(result['state_tax_receipts_yoy_growth'], float)
    
    def test_calculate_fiscal_indicators_insufficient_data(self):
        """Test fiscal indicators calculation with insufficient data."""
        fetcher = FreeDataFetcher("fred_key")
        
        # Mock fiscal data with insufficient tax data
        fiscal_data = {
            'state_code': 'CA',
            'tax_receipts_data': [
                {'date': datetime(2023, 12, 31), 'value': 1100.0}  # Only one data point
            ],
            'gsp_data': [],
            'national_budget_data': [],
            'national_tax_data': []
        }
        
        result = fetcher.calculate_fiscal_indicators(fiscal_data)
        
        assert result is not None
        assert result['state_tax_receipts_yoy_growth'] is None
        assert result['state_budget_surplus_deficit_as_pct_of_gsp'] is None
    
    def test_simple_budget_estimation(self):
        """Test simple budget estimation fallback."""
        fetcher = FreeDataFetcher("fred_key")
        
        fiscal_data = {
            'tax_receipts_data': [
                {'date': datetime(2022, 12, 31), 'value': 1000.0},
                {'date': datetime(2023, 12, 31), 'value': 1100.0}
            ]
        }
        
        indicators = {
            'state_tax_receipts_yoy_growth': 10.0,  # High growth
            'state_budget_surplus_deficit_as_pct_of_gsp': None
        }
        
        fetcher._simple_budget_estimation(fiscal_data, indicators)
        
        # Should have estimated a budget balance
        assert indicators['state_budget_surplus_deficit_as_pct_of_gsp'] is not None
        assert isinstance(indicators['state_budget_surplus_deficit_as_pct_of_gsp'], float)


class TestFreeAPIErrorHandling:
    """Test API error handling."""
    
    def test_api_error_creation(self):
        """Test FreeAPIError exception creation."""
        error = FreeAPIError("Test error message")
        assert str(error) == "Test error message"
    
    @patch('requests.Session.get')
    def test_fred_client_network_error(self, mock_get):
        """Test FRED API network error handling."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
        
        api = FREDAPIClient("test_key")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        # Should return empty list on network error
        result = api.get_state_tax_collections("CA", start_date, end_date)
        assert result == []


class TestDataProcessing:
    """Test data processing utilities."""
    
    def test_data_flow_integration(self):
        """Test complete data flow from fetch to calculation."""
        fetcher = FreeDataFetcher("test_key")
        
        # Test with mock data that simulates real API response structure
        with patch.object(fetcher.fred_client, 'get_state_tax_collections') as mock_tax, \
             patch.object(fetcher.fred_client, 'get_state_gsp') as mock_gsp, \
             patch.object(fetcher.fred_client, 'get_national_budget_balance') as mock_budget, \
             patch.object(fetcher.fred_client, 'get_national_tax_totals') as mock_tax_totals:
            
            # Setup mocks
            mock_tax.return_value = [
                {'date': datetime(2022, 12, 31), 'value': 1000.0},
                {'date': datetime(2023, 3, 31), 'value': 1020.0},
                {'date': datetime(2023, 6, 30), 'value': 1040.0},
                {'date': datetime(2023, 9, 30), 'value': 1060.0},
                {'date': datetime(2023, 12, 31), 'value': 1100.0}
            ]
            mock_gsp.return_value = [
                {'date': datetime(2023, 12, 31), 'value': 25000.0}
            ]
            mock_budget.return_value = [
                {'date': datetime(2023, 12, 31), 'value': 500.0}
            ]
            mock_tax_totals.return_value = [
                {'date': datetime(2023, 12, 31), 'value': 50000.0}
            ]
            
            # Test complete workflow
            fiscal_data = fetcher.fetch_state_fiscal_data("CA", datetime(2023, 12, 31))
            indicators = fetcher.calculate_fiscal_indicators(fiscal_data)
            
            # Verify results
            assert fiscal_data is not None
            assert indicators is not None
            assert 'state_tax_receipts_yoy_growth' in indicators
            assert 'state_budget_surplus_deficit_as_pct_of_gsp' in indicators