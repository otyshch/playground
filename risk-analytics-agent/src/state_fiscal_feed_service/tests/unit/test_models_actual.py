"""
Unit tests for data models - Updated to match actual implementation.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from src.shared.models import (
    StateFiscalDataCreate,
    StateFiscalDataResponse,
    StateFiscalData,
    BulkExportRequest,
    HealthCheckResponse
)


class TestStateFiscalDataCreate:
    """Test StateFiscalDataCreate model."""
    
    def test_create_valid_record(self):
        """Test creating a valid fiscal data record."""
        data = StateFiscalDataCreate(
            state_code="CA",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2
        )
        
        assert data.state_code == "CA"
        assert data.data_timestamp == datetime(2023, 12, 31)
        assert data.state_tax_receipts_yoy_growth == 3.5
        assert data.state_budget_surplus_deficit_as_pct_of_gsp == -1.2
    
    def test_invalid_state_code(self):
        """Test validation of invalid state codes."""
        with pytest.raises(ValidationError):
            StateFiscalDataCreate(
                state_code="INVALID",
                data_timestamp=datetime(2023, 12, 31),
                state_tax_receipts_yoy_growth=3.5,
                state_budget_surplus_deficit_as_pct_of_gsp=-1.2
            )
    
    def test_state_code_case_insensitive(self):
        """Test that state codes are normalized to uppercase."""
        data = StateFiscalDataCreate(
            state_code="ca",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2
        )
        
        assert data.state_code == "CA"
    
    def test_future_date_validation(self):
        """Test validation of future dates."""
        future_date = datetime(2030, 1, 1)
        
        with pytest.raises(ValidationError):
            StateFiscalDataCreate(
                state_code="CA",
                data_timestamp=future_date,
                state_tax_receipts_yoy_growth=3.5,
                state_budget_surplus_deficit_as_pct_of_gsp=-1.2
            )
    
    def test_extreme_values_validation(self):
        """Test validation of extreme values."""
        # Test extremely high growth rate
        with pytest.raises(ValidationError):
            StateFiscalDataCreate(
                state_code="CA",
                data_timestamp=datetime(2023, 12, 31),
                state_tax_receipts_yoy_growth=1000.0,  # 1000% growth
                state_budget_surplus_deficit_as_pct_of_gsp=-1.2
            )
        
        # Test extremely low growth rate
        with pytest.raises(ValidationError):
            StateFiscalDataCreate(
                state_code="CA",
                data_timestamp=datetime(2023, 12, 31),
                state_tax_receipts_yoy_growth=-200.0,  # -200% growth
                state_budget_surplus_deficit_as_pct_of_gsp=-1.2
            )


class TestStateFiscalDataResponse:
    """Test StateFiscalDataResponse model."""
    
    def test_response_model_creation(self):
        """Test creating a response model."""
        data = StateFiscalDataResponse(
            state_code="CA",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2
        )
        
        assert data.state_code == "CA"
        assert data.data_timestamp == datetime(2023, 12, 31)
        assert data.state_tax_receipts_yoy_growth == 3.5
        assert data.state_budget_surplus_deficit_as_pct_of_gsp == -1.2
    
    def test_response_with_none_values(self):
        """Test response model with None values."""
        data = StateFiscalDataResponse(
            state_code="CA",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=None,
            state_budget_surplus_deficit_as_pct_of_gsp=None
        )
        
        assert data.state_code == "CA"
        assert data.state_tax_receipts_yoy_growth is None
        assert data.state_budget_surplus_deficit_as_pct_of_gsp is None


class TestBulkExportRequest:
    """Test BulkExportRequest model."""
    
    def test_bulk_export_request_creation(self):
        """Test creating a bulk export request."""
        request = BulkExportRequest(
            states=["CA", "NY", "TX"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            format="csv"
        )
        
        assert request.states == ["CA", "NY", "TX"]
        assert request.start_date == datetime(2023, 1, 1)
        assert request.end_date == datetime(2023, 12, 31)
        assert request.format == "csv"
    
    def test_bulk_export_invalid_format(self):
        """Test validation of invalid export format."""
        with pytest.raises(ValidationError):
            BulkExportRequest(
                states=["CA", "NY"],
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
                format="xml"  # Invalid format
            )
    
    def test_bulk_export_date_range_validation(self):
        """Test validation of date ranges."""
        # End date before start date
        with pytest.raises(ValidationError):
            BulkExportRequest(
                states=["CA", "NY"],
                start_date=datetime(2023, 12, 31),
                end_date=datetime(2023, 1, 1),
                format="csv"
            )
    
    def test_bulk_export_empty_states(self):
        """Test validation of empty states list."""
        with pytest.raises(ValidationError):
            BulkExportRequest(
                states=[],
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
                format="csv"
            )


class TestHealthCheckResponse:
    """Test HealthCheckResponse model."""
    
    def test_health_check_response_creation(self):
        """Test creating a health check response."""
        response = HealthCheckResponse(
            status="healthy",
            timestamp=datetime(2023, 12, 31),
            version="1.0.0",
            database_status="connected",
            external_apis_status="operational"
        )
        
        assert response.status == "healthy"
        assert response.timestamp == datetime(2023, 12, 31)
        assert response.version == "1.0.0"
        assert response.database_status == "connected"
        assert response.external_apis_status == "operational"
    
    def test_health_check_response_defaults(self):
        """Test health check response with default values."""
        response = HealthCheckResponse(
            status="healthy",
            timestamp=datetime(2023, 12, 31),
            version="1.0.0"
        )
        
        assert response.status == "healthy"
        assert response.database_status == "unknown"
        assert response.external_apis_status == "unknown"


class TestModelSerialization:
    """Test model serialization and deserialization."""
    
    def test_json_serialization(self):
        """Test JSON serialization of models."""
        data = StateFiscalDataCreate(
            state_code="CA",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2
        )
        
        json_data = data.model_dump()
        
        assert json_data["state_code"] == "CA"
        assert json_data["state_tax_receipts_yoy_growth"] == 3.5
        assert json_data["state_budget_surplus_deficit_as_pct_of_gsp"] == -1.2
    
    def test_json_deserialization(self):
        """Test JSON deserialization of models."""
        json_data = {
            "state_code": "CA",
            "data_timestamp": "2023-12-31T00:00:00",
            "state_tax_receipts_yoy_growth": 3.5,
            "state_budget_surplus_deficit_as_pct_of_gsp": -1.2
        }
        
        data = StateFiscalDataCreate(**json_data)
        
        assert data.state_code == "CA"
        assert data.state_tax_receipts_yoy_growth == 3.5
        assert data.state_budget_surplus_deficit_as_pct_of_gsp == -1.2


class TestFieldValidation:
    """Test specific field validation rules."""
    
    def test_state_code_length_validation(self):
        """Test state code length validation."""
        # Too short
        with pytest.raises(ValidationError):
            StateFiscalDataCreate(
                state_code="C",
                data_timestamp=datetime(2023, 12, 31),
                state_tax_receipts_yoy_growth=3.5,
                state_budget_surplus_deficit_as_pct_of_gsp=-1.2
            )
        
        # Too long
        with pytest.raises(ValidationError):
            StateFiscalDataCreate(
                state_code="CAL",
                data_timestamp=datetime(2023, 12, 31),
                state_tax_receipts_yoy_growth=3.5,
                state_budget_surplus_deficit_as_pct_of_gsp=-1.2
            )
    
    def test_numeric_field_precision(self):
        """Test numeric field precision handling."""
        data = StateFiscalDataCreate(
            state_code="CA",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=3.123456789,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.987654321
        )
        
        # Should maintain precision
        assert data.state_tax_receipts_yoy_growth == 3.123456789
        assert data.state_budget_surplus_deficit_as_pct_of_gsp == -1.987654321
    
    def test_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError):
            StateFiscalDataCreate(
                # Missing state_code
                data_timestamp=datetime(2023, 12, 31),
                state_tax_receipts_yoy_growth=3.5,
                state_budget_surplus_deficit_as_pct_of_gsp=-1.2
            )
        
        with pytest.raises(ValidationError):
            StateFiscalDataCreate(
                state_code="CA",
                # Missing data_timestamp
                state_tax_receipts_yoy_growth=3.5,
                state_budget_surplus_deficit_as_pct_of_gsp=-1.2
            )