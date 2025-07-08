"""
Unit tests for configuration management.
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
        assert settings.database_url == "postgresql://postgres:postgres@localhost:5433/state_fiscal_feed"
        assert settings.database_pool_size == 10
        assert settings.database_max_overflow == 20
        
        # API configuration
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.api_workers == 1
        assert settings.enable_cors is True
        
        # Logging configuration
        assert settings.log_level == "INFO"
        assert settings.enable_structured_logging is True
        
        # Rate limiting
        assert settings.rate_limit_requests == 100
        assert settings.rate_limit_window == 60
        
        # Data ingestion
        assert settings.enable_data_validation is True
        assert settings.enable_forward_fill is True
        assert settings.forward_fill_max_days == 30
        assert settings.data_retention_days == 365
    
    def test_environment_variable_override(self):
        """Test environment variable configuration override."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://test:test@test:5432/test',
            'API_PORT': '9000',
            'LOG_LEVEL': 'DEBUG',
            'ENABLE_CORS': 'false',
            'RATE_LIMIT_REQUESTS': '200'
        }):
            settings = Settings()
            
            assert settings.database_url == 'postgresql://test:test@test:5432/test'
            assert settings.api_port == 9000
            assert settings.log_level == 'DEBUG'
            assert settings.enable_cors is False
            assert settings.rate_limit_requests == 200
    
    def test_redis_url_configuration(self):
        """Test Redis URL configuration."""
        # Default Redis URL
        settings = Settings()
        assert settings.redis_url == "redis://localhost:6379/0"
        
        # Environment override
        with patch.dict(os.environ, {'REDIS_URL': 'redis://test:6380/1'}):
            settings = Settings()
            assert settings.redis_url == 'redis://test:6380/1'
    
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
            with patch.dict(os.environ, {'ENABLE_CORS': env_value}):
                settings = Settings()
                assert settings.enable_cors == expected
    
    def test_integer_configuration_validation(self):
        """Test integer configuration validation."""
        # Valid integer values
        with patch.dict(os.environ, {'API_PORT': '8080'}):
            settings = Settings()
            assert settings.api_port == 8080
        
        # Invalid integer values should raise validation error
        with patch.dict(os.environ, {'API_PORT': 'invalid'}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_ingestion_configuration(self):
        """Test data ingestion specific configuration."""
        settings = Settings()
        
        # Default ingestion settings
        assert settings.ingestion_batch_size == 50
        assert settings.ingestion_concurrent_requests == 10
        assert settings.ingestion_retry_attempts == 3
        assert settings.ingestion_retry_delay == 1.0
        
        # Environment overrides
        with patch.dict(os.environ, {
            'INGESTION_BATCH_SIZE': '100',
            'INGESTION_CONCURRENT_REQUESTS': '20',
            'INGESTION_RETRY_ATTEMPTS': '5',
            'INGESTION_RETRY_DELAY': '2.5'
        }):
            settings = Settings()
            assert settings.ingestion_batch_size == 100
            assert settings.ingestion_concurrent_requests == 20
            assert settings.ingestion_retry_attempts == 5
            assert settings.ingestion_retry_delay == 2.5
    
    def test_monitoring_configuration(self):
        """Test monitoring and metrics configuration."""
        settings = Settings()
        
        # Default monitoring settings
        assert settings.enable_metrics is True
        assert settings.metrics_port == 9090
        assert settings.enable_health_checks is True
        
        # Environment overrides
        with patch.dict(os.environ, {
            'ENABLE_METRICS': 'false',
            'METRICS_PORT': '9091',
            'ENABLE_HEALTH_CHECKS': 'false'
        }):
            settings = Settings()
            assert settings.enable_metrics is False
            assert settings.metrics_port == 9091
            assert settings.enable_health_checks is False


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


class TestConfigurationValidation:
    """Test configuration validation and error handling."""
    
    def test_invalid_log_level(self):
        """Test validation of invalid log level."""
        with patch.dict(os.environ, {'LOG_LEVEL': 'INVALID'}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_negative_port_number(self):
        """Test validation of negative port numbers."""
        with patch.dict(os.environ, {'API_PORT': '-1'}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_port_number_too_high(self):
        """Test validation of port numbers above valid range."""
        with patch.dict(os.environ, {'API_PORT': '70000'}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_negative_rate_limit(self):
        """Test validation of negative rate limit values."""
        with patch.dict(os.environ, {'RATE_LIMIT_REQUESTS': '-1'}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_negative_retention_days(self):
        """Test validation of negative retention days."""
        with patch.dict(os.environ, {'DATA_RETENTION_DAYS': '-1'}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_invalid_database_url_format(self):
        """Test validation of database URL format."""
        with patch.dict(os.environ, {'DATABASE_URL': 'invalid-url'}):
            # This might not raise an error during settings creation
            # but would fail when trying to connect
            settings = Settings()
            assert settings.database_url == 'invalid-url'
    
    def test_missing_required_api_keys_in_production(self):
        """Test handling of missing API keys in production."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'FRED_API_KEY': '',
            'TRADING_ECONOMICS_API_KEY': ''
        }):
            # In production, missing API keys might be a warning rather than error
            settings = Settings()
            assert settings.fred_api_key == ''
            assert settings.trading_economics_api_key == ''


class TestDevelopmentConfiguration:
    """Test development-specific configuration."""
    
    def test_development_mode_settings(self):
        """Test settings for development mode."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'DEBUG': 'true'
        }):
            settings = Settings()
            assert settings.debug is True
            # Development mode might have different defaults
    
    def test_testing_mode_settings(self):
        """Test settings for testing mode."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'testing',
            'LOG_LEVEL': 'DEBUG'
        }):
            settings = Settings()
            assert settings.log_level == 'DEBUG'
    
    def test_production_mode_settings(self):
        """Test settings for production mode."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'DEBUG': 'false',
            'LOG_LEVEL': 'WARNING'
        }):
            settings = Settings()
            assert settings.debug is False
            assert settings.log_level == 'WARNING'