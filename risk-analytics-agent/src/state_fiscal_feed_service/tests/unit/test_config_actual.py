"""
Unit tests for configuration management - Updated to match actual implementation.
"""
import pytest
import os
from unittest.mock import patch

from src.shared.config import Settings, get_settings, US_STATE_CODES, STATE_NAMES


class TestSettings:
    """Test configuration settings."""
    
    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()
        
        # Database configuration
        assert settings.database_url == "postgresql://postgres:postgres@localhost:5432/state_fiscal_feed"
        
        # API configuration
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.debug is False
        
        # Logging configuration
        assert settings.log_level == "INFO"
        
        # Data ingestion
        assert settings.enable_data_validation is True
        assert settings.enable_forward_fill is True
        assert settings.data_retention_days == 2555
    
    def test_environment_variable_override(self):
        """Test environment variable configuration override."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@test:5432/test',
            'API_PORT': '9000',
            'LOG_LEVEL': 'DEBUG',
            'DEBUG': 'true'
        }):
            settings = Settings()
            
            assert settings.database_url == 'postgresql://test:test@test:5432/test'
            assert settings.api_port == 9000
            assert settings.log_level == 'DEBUG'
            assert settings.debug is True
    
    def test_api_key_configuration(self):
        """Test API key configuration."""
        settings = Settings()
        
        # Default values (empty)
        assert settings.fred_api_key == ""
        assert settings.trading_economics_api_key == ""
        
        # Environment override
        with patch.dict(os.environ, {
            'FRED_API_KEY': 'test_fred_key',
            'TRADING_ECONOMICS_API_KEY': 'test_te_key'
        }):
            settings = Settings()
            assert settings.fred_api_key == 'test_fred_key'
            assert settings.trading_economics_api_key == 'test_te_key'
    
    def test_boolean_configuration(self):
        """Test boolean configuration parsing."""
        # Test various boolean representations
        bool_values = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('1', True),
            ('yes', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('0', False),
            ('no', False),
            ('', False)
        ]
        
        for env_value, expected in bool_values:
            with patch.dict(os.environ, {'DEBUG': env_value}):
                settings = Settings()
                assert settings.debug == expected
    
    def test_ingestion_configuration(self):
        """Test data ingestion specific configuration."""
        settings = Settings()
        
        # Default ingestion settings
        assert settings.ingestion_schedule_minutes == 60
        assert settings.data_retention_days == 2555
        
        # Environment overrides
        with patch.dict(os.environ, {
            'INGESTION_SCHEDULE_MINUTES': '120',
            'DATA_RETENTION_DAYS': '365'
        }):
            settings = Settings()
            assert settings.ingestion_schedule_minutes == 120
            assert settings.data_retention_days == 365
    
    def test_monitoring_configuration(self):
        """Test monitoring and metrics configuration."""
        settings = Settings()
        
        # Default monitoring settings
        assert settings.enable_metrics is True
        assert settings.metrics_port == 8080
        
        # Environment overrides
        with patch.dict(os.environ, {
            'ENABLE_METRICS': 'false',
            'METRICS_PORT': '9091'
        }):
            settings = Settings()
            assert settings.enable_metrics is False
            assert settings.metrics_port == 9091


class TestGetSettings:
    """Test settings singleton function."""
    
    def test_get_settings_singleton(self):
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should be the same instance
        assert settings1 is settings2
    
    def test_get_settings_configuration(self):
        """Test that get_settings returns properly configured settings."""
        settings = get_settings()
        
        # Should have all required attributes
        assert hasattr(settings, 'database_url')
        assert hasattr(settings, 'api_host')
        assert hasattr(settings, 'api_port')
        assert hasattr(settings, 'fred_api_key')
        assert hasattr(settings, 'log_level')


class TestStateConstants:
    """Test state code and name constants."""
    
    def test_us_state_codes_validity(self):
        """Test that all US state codes are valid."""
        # Should have 50 states
        assert len(US_STATE_CODES) == 50
        
        # All codes should be 2 characters
        for code in US_STATE_CODES:
            assert len(code) == 2
            assert code.isupper()
            assert code.isalpha()
        
        # Check for some known states
        assert "CA" in US_STATE_CODES
        assert "NY" in US_STATE_CODES
        assert "TX" in US_STATE_CODES
        assert "FL" in US_STATE_CODES
        assert "WY" in US_STATE_CODES
    
    def test_us_state_names_validity(self):
        """Test that all US state names are valid."""
        # Should have same number as codes
        assert len(STATE_NAMES) == len(US_STATE_CODES)
        
        # All names should be non-empty strings
        for name in STATE_NAMES.values():
            assert isinstance(name, str)
            assert len(name) > 0
        
        # Check for some known mappings
        assert STATE_NAMES["CA"] == "California"
        assert STATE_NAMES["NY"] == "New York"
        assert STATE_NAMES["TX"] == "Texas"
        assert STATE_NAMES["FL"] == "Florida"
    
    def test_state_codes_and_names_consistency(self):
        """Test consistency between state codes and names."""
        # Every state code should have a corresponding name
        for code in US_STATE_CODES:
            assert code in STATE_NAMES
        
        # Every state name should have a corresponding code
        for code in STATE_NAMES:
            assert code in US_STATE_CODES
    
    def test_no_duplicate_state_codes(self):
        """Test that there are no duplicate state codes."""
        assert len(US_STATE_CODES) == len(set(US_STATE_CODES))
    
    def test_no_duplicate_state_names(self):
        """Test that there are no duplicate state names."""
        names = list(STATE_NAMES.values())
        assert len(names) == len(set(names))