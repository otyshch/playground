"""
Unit tests for data models.
"""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from src.shared.models import StateFiscalData, StateFiscalDataCreate, StateFiscalDataResponse, StateFiscalIndicators


class TestStateFiscalData:
    """Test SQLAlchemy model for state fiscal data."""
    
    def test_create_valid_record(self, test_db_session):
        """Test creating a valid fiscal data record."""
        fiscal_data = StateFiscalData(
            state_code="CA",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2
        )
        
        test_db_session.add(fiscal_data)
        test_db_session.commit()
        
        # Verify record was created
        assert fiscal_data.id is not None
        assert fiscal_data.state_code == "CA"
        assert fiscal_data.state_tax_receipts_yoy_growth == 3.5
        assert fiscal_data.state_budget_surplus_deficit_as_pct_of_gsp == -1.2
        assert fiscal_data.created_at is not None
        assert fiscal_data.updated_at is not None
    
    def test_state_code_required(self, test_db_session):
        """Test that state_code is required."""
        fiscal_data = StateFiscalData(
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2
        )
        
        test_db_session.add(fiscal_data)
        
        with pytest.raises(IntegrityError):
            test_db_session.commit()
    
    def test_data_timestamp_required(self, test_db_session):
        """Test that data_timestamp is required."""
        fiscal_data = StateFiscalData(
            state_code="CA",
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2
        )
        
        test_db_session.add(fiscal_data)
        
        with pytest.raises(IntegrityError):
            test_db_session.commit()
    
    def test_query_by_state_and_date(self, test_db_session, sample_fiscal_data):
        """Test querying records by state and date."""
        target_date = datetime(2023, 12, 31)
        
        records = test_db_session.query(StateFiscalData).filter(
            StateFiscalData.state_code == "CA",
            StateFiscalData.data_timestamp == target_date
        ).all()
        
        assert len(records) == 1
        assert records[0].state_code == "CA"
        assert records[0].data_timestamp == target_date


class TestStateFiscalDataCreate:
    """Test Pydantic model for creating fiscal data."""
    
    def test_valid_creation(self):
        """Test creating valid fiscal data creation model."""
        fiscal_data = StateFiscalDataCreate(
            state_code="CA",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2
        )
        
        assert fiscal_data.state_code == "CA"
        assert fiscal_data.data_timestamp == datetime(2023, 12, 31)
        assert fiscal_data.state_tax_receipts_yoy_growth == 3.5
        assert fiscal_data.state_budget_surplus_deficit_as_pct_of_gsp == -1.2
    
    def test_state_code_validation(self):
        """Test state code validation."""
        with pytest.raises(ValueError):
            StateFiscalDataCreate(
                state_code="CAL",  # Invalid - too long
                data_timestamp=datetime(2023, 12, 31),
                state_tax_receipts_yoy_growth=3.5,
                state_budget_surplus_deficit_as_pct_of_gsp=-1.2
            )


class TestStateFiscalDataResponse:
    """Test response model for fiscal data API."""
    
    def test_valid_response(self):
        """Test creating valid response model."""
        indicators = StateFiscalIndicators(
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2
        )
        
        response = StateFiscalDataResponse(
            data_timestamp=datetime(2023, 12, 31),
            state="CA",
            state_fiscal_indicators=indicators
        )
        
        assert response.data_timestamp == datetime(2023, 12, 31)
        assert response.state == "CA"
        assert response.state_fiscal_indicators.state_tax_receipts_yoy_growth == 3.5
        assert response.state_fiscal_indicators.state_budget_surplus_deficit_as_pct_of_gsp == -1.2
    
    def test_json_serialization(self):
        """Test JSON serialization of response model."""
        indicators = StateFiscalIndicators(
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2
        )
        
        response = StateFiscalDataResponse(
            data_timestamp=datetime(2023, 12, 31),
            state="CA",
            state_fiscal_indicators=indicators
        )
        
        json_data = response.model_dump()
        
        assert json_data["state"] == "CA"
        assert json_data["state_fiscal_indicators"]["state_tax_receipts_yoy_growth"] == 3.5
        assert json_data["state_fiscal_indicators"]["state_budget_surplus_deficit_as_pct_of_gsp"] == -1.2