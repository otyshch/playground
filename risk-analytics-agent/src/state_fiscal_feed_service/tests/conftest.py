"""
Pytest configuration and fixtures.
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.shared.database import DatabaseManager
from src.shared.models import Base, StateFiscalData
from src.shared.config import Settings
from src.api.main import create_app


@pytest.fixture(scope="session")
def test_database_url():
    """Create a temporary test database."""
    # Use SQLite for testing
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()
    database_url = f"sqlite:///{temp_db.name}"
    yield database_url
    # Cleanup
    os.unlink(temp_db.name)


@pytest.fixture(scope="session")
def test_settings(test_database_url):
    """Create test settings."""
    return Settings(
        database_url=test_database_url,
        redis_url="redis://localhost:6379/15",  # Test database
        trading_economics_api_key="test_key",
        fred_api_key="test_key",
        debug=True,
        log_level="DEBUG"
    )


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """Create test database engine."""
    engine = create_engine(test_database_url, echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db_session(test_engine):
    """Create a test database session."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_app(test_settings, test_db_session):
    """Create test FastAPI application."""
    app = create_app()
    
    # Override dependencies
    from src.shared.database import get_db
    from src.api.dependencies import get_fiscal_service
    from src.api.services.fiscal_service import FiscalDataService
    
    def override_get_db():
        yield test_db_session
    
    def override_get_fiscal_service():
        service = FiscalDataService()
        service.db_manager = DatabaseManager(test_settings.database_url)
        return service
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_fiscal_service] = override_get_fiscal_service
    
    return app


@pytest.fixture
def test_client(test_app):
    """Create test HTTP client."""
    with TestClient(test_app) as client:
        yield client


@pytest.fixture
def sample_fiscal_data(test_db_session):
    """Create sample fiscal data for testing."""
    sample_data = [
        StateFiscalData(
            state_code="CA",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=3.5,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.2
        ),
        StateFiscalData(
            state_code="NY",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=2.8,
            state_budget_surplus_deficit_as_pct_of_gsp=0.5
        ),
        StateFiscalData(
            state_code="TX",
            data_timestamp=datetime(2023, 12, 31),
            state_tax_receipts_yoy_growth=4.1,
            state_budget_surplus_deficit_as_pct_of_gsp=1.8
        ),
        # Historical data for CA
        StateFiscalData(
            state_code="CA",
            data_timestamp=datetime(2023, 11, 30),
            state_tax_receipts_yoy_growth=3.2,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.5
        ),
        StateFiscalData(
            state_code="CA",
            data_timestamp=datetime(2023, 10, 31),
            state_tax_receipts_yoy_growth=2.9,
            state_budget_surplus_deficit_as_pct_of_gsp=-1.8
        )
    ]
    
    for data in sample_data:
        test_db_session.add(data)
    test_db_session.commit()
    
    return sample_data


@pytest.fixture
def mock_external_api_response():
    """Mock response from external APIs."""
    return {
        "trading_economics": [
            {
                "country": "United States",
                "category": "Tax Revenue",
                "datetime": "2023-12-31",
                "value": 150.5,
                "frequency": "Monthly"
            }
        ],
        "fred": {
            "observations": [
                {
                    "date": "2023-12-31",
                    "value": "25000.0"
                }
            ]
        }
    }


@pytest.fixture
def test_state_codes():
    """Common test state codes."""
    return ["CA", "NY", "TX", "FL"]


@pytest.fixture
def test_date_range():
    """Common test date range."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    return start_date, end_date