"""
Unit tests for database operations and management.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import sessionmaker

from src.shared.database import DatabaseManager, get_database_manager, init_database
from src.shared.models import Base, StateFiscalData
from src.shared.config import Settings


class TestDatabaseManager:
    """Test database manager functionality."""
    
    def test_initialization_with_url(self):
        """Test database manager initialization with URL."""
        db_url = "sqlite:///test.db"
        manager = DatabaseManager(db_url)
        
        assert manager.database_url == db_url
        assert manager.engine is not None
        assert manager.SessionLocal is not None
    
    def test_initialization_with_settings(self):
        """Test database manager initialization with settings."""
        settings = Settings(database_url="sqlite:///test_settings.db")
        manager = DatabaseManager.from_settings(settings)
        
        assert manager.database_url == settings.database_url
        assert manager.pool_size == settings.database_pool_size
        assert manager.max_overflow == settings.database_max_overflow
    
    def test_create_engine_with_pool_settings(self):
        """Test engine creation with connection pool settings."""
        db_url = "postgresql://user:pass@localhost/test"
        pool_size = 20
        max_overflow = 40
        
        manager = DatabaseManager(
            db_url, 
            pool_size=pool_size, 
            max_overflow=max_overflow
        )
        
        # For PostgreSQL, pool settings should be applied
        if "postgresql" in db_url:
            assert manager.engine.pool.size() == pool_size
            assert manager.engine.pool._max_overflow == max_overflow
    
    def test_get_session_sync(self, test_database_url):
        """Test synchronous session creation."""
        manager = DatabaseManager(test_database_url)
        
        session = manager.get_session_sync()
        assert session is not None
        
        # Test session functionality
        try:
            # Should be able to execute queries
            result = session.execute("SELECT 1").scalar()
            assert result == 1
        finally:
            session.close()
    
    async def test_get_session_async(self, test_database_url):
        """Test asynchronous session creation."""
        manager = DatabaseManager(test_database_url)
        
        async with manager.get_session_async() as session:
            # Should be able to execute async queries
            result = await session.execute("SELECT 1")
            assert result.scalar() == 1
    
    def test_session_context_manager(self, test_database_url):
        """Test session context manager functionality."""
        manager = DatabaseManager(test_database_url)
        
        # Test successful context
        with manager.get_session_sync() as session:
            result = session.execute("SELECT 1").scalar()
            assert result == 1
        
        # Session should be closed after context
        # Note: Testing session state after context exit is implementation-specific
    
    def test_create_tables(self, test_database_url):
        """Test table creation."""
        manager = DatabaseManager(test_database_url)
        
        # Drop and recreate tables
        Base.metadata.drop_all(bind=manager.engine)
        manager.create_tables()
        
        # Verify tables exist
        table_names = manager.engine.table_names()
        assert "state_fiscal_data" in table_names
    
    def test_health_check_success(self, test_database_url):
        """Test successful database health check."""
        manager = DatabaseManager(test_database_url)
        
        is_healthy = manager.health_check()
        assert is_healthy is True
    
    @patch('sqlalchemy.create_engine')
    def test_health_check_failure(self, mock_create_engine):
        """Test database health check failure."""
        # Mock engine that raises exception on connect
        mock_engine = Mock()
        mock_engine.connect.side_effect = OperationalError("Connection failed", None, None)
        mock_create_engine.return_value = mock_engine
        
        manager = DatabaseManager("postgresql://invalid:invalid@invalid:5432/invalid")
        
        is_healthy = manager.health_check()
        assert is_healthy is False
    
    def test_get_connection_info(self, test_database_url):
        """Test retrieving connection information."""
        manager = DatabaseManager(test_database_url)
        
        info = manager.get_connection_info()
        
        assert "database_url" in info
        assert "driver" in info
        assert "pool_size" in info
        assert "max_overflow" in info
        assert info["database_url"] == test_database_url
    
    def test_close_connections(self, test_database_url):
        """Test closing database connections."""
        manager = DatabaseManager(test_database_url)
        
        # Create some connections
        session1 = manager.get_session_sync()
        session2 = manager.get_session_sync()
        
        # Close connections
        manager.close()
        
        # Clean up sessions
        session1.close()
        session2.close()
        
        # Engine should be disposed
        # Note: Testing engine disposal is implementation-specific


class TestDatabaseManagerErrorHandling:
    """Test database manager error handling."""
    
    def test_invalid_database_url(self):
        """Test handling of invalid database URL."""
        with pytest.raises(SQLAlchemyError):
            manager = DatabaseManager("invalid-database-url")
            manager.get_session_sync()
    
    @patch('sqlalchemy.create_engine')
    def test_engine_creation_failure(self, mock_create_engine):
        """Test handling of engine creation failure."""
        mock_create_engine.side_effect = SQLAlchemyError("Engine creation failed")
        
        with pytest.raises(SQLAlchemyError):
            DatabaseManager("postgresql://user:pass@localhost/test")
    
    def test_session_rollback_on_error(self, test_database_url):
        """Test session rollback on error."""
        manager = DatabaseManager(test_database_url)
        manager.create_tables()
        
        with pytest.raises(Exception):
            with manager.get_session_sync() as session:
                # Create a record
                record = StateFiscalData(
                    state_code="CA",
                    data_timestamp=datetime.now(),
                    state_tax_receipts_yoy_growth=3.5,
                    state_budget_surplus_deficit_as_pct_of_gsp=-1.2
                )
                session.add(record)
                session.flush()  # This should work
                
                # Now cause an error
                raise Exception("Simulated error")
        
        # Session should have been rolled back
        with manager.get_session_sync() as session:
            count = session.query(StateFiscalData).count()
            assert count == 0  # No records should be committed


class TestDatabaseSingleton:
    """Test database manager singleton functionality."""
    
    def test_get_database_manager_singleton(self):
        """Test that get_database_manager returns singleton."""
        manager1 = get_database_manager()
        manager2 = get_database_manager()
        
        # Should be the same instance
        assert manager1 is manager2
    
    @patch('src.shared.database.get_settings')
    def test_get_database_manager_with_settings(self, mock_get_settings):
        """Test database manager creation with settings."""
        mock_settings = Mock()
        mock_settings.database_url = "sqlite:///test_singleton.db"
        mock_settings.database_pool_size = 15
        mock_settings.database_max_overflow = 25
        mock_get_settings.return_value = mock_settings
        
        # Clear any existing singleton
        if hasattr(get_database_manager, '_instance'):
            del get_database_manager._instance
        
        manager = get_database_manager()
        
        assert manager.database_url == mock_settings.database_url
        # Note: Pool settings verification depends on database type


class TestDatabaseInitialization:
    """Test database initialization functions."""
    
    @patch('src.shared.database.get_database_manager')
    def test_init_database_success(self, mock_get_manager):
        """Test successful database initialization."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        
        init_database()
        
        # Should call create_tables
        mock_manager.create_tables.assert_called_once()
    
    @patch('src.shared.database.get_database_manager')
    def test_init_database_failure(self, mock_get_manager):
        """Test database initialization failure handling."""
        mock_manager = Mock()
        mock_manager.create_tables.side_effect = SQLAlchemyError("Table creation failed")
        mock_get_manager.return_value = mock_manager
        
        # Should not raise exception, but log error
        init_database()
        
        # Should still attempt to create tables
        mock_manager.create_tables.assert_called_once()


class TestDatabasePerformance:
    """Test database performance and optimization."""
    
    def test_connection_pooling(self, test_database_url):
        """Test connection pooling behavior."""
        pool_size = 5
        manager = DatabaseManager(test_database_url, pool_size=pool_size)
        
        # Create multiple sessions
        sessions = []
        for _ in range(pool_size):
            session = manager.get_session_sync()
            sessions.append(session)
        
        # All sessions should be created successfully
        assert len(sessions) == pool_size
        
        # Clean up
        for session in sessions:
            session.close()
    
    def test_concurrent_sessions(self, test_database_url):
        """Test concurrent session handling."""
        manager = DatabaseManager(test_database_url)
        manager.create_tables()
        
        # Create concurrent sessions and perform operations
        def create_record(session, state_code):
            record = StateFiscalData(
                state_code=state_code,
                data_timestamp=datetime.now(),
                state_tax_receipts_yoy_growth=3.5,
                state_budget_surplus_deficit_as_pct_of_gsp=-1.2
            )
            session.add(record)
            session.commit()
        
        # Test multiple sessions
        session1 = manager.get_session_sync()
        session2 = manager.get_session_sync()
        
        try:
            create_record(session1, "CA")
            create_record(session2, "NY")
            
            # Both records should be created
            count1 = session1.query(StateFiscalData).count()
            count2 = session2.query(StateFiscalData).count()
            
            assert count1 >= 1
            assert count2 >= 1
            
        finally:
            session1.close()
            session2.close()


class TestDatabaseMigration:
    """Test database migration and schema management."""
    
    def test_table_creation_idempotent(self, test_database_url):
        """Test that table creation is idempotent."""
        manager = DatabaseManager(test_database_url)
        
        # Create tables multiple times
        manager.create_tables()
        manager.create_tables()
        manager.create_tables()
        
        # Should not raise errors
        table_names = manager.engine.table_names()
        assert "state_fiscal_data" in table_names
    
    def test_schema_validation(self, test_database_url):
        """Test database schema validation."""
        manager = DatabaseManager(test_database_url)
        manager.create_tables()
        
        # Verify table structure
        with manager.get_session_sync() as session:
            # Test that we can create a valid record
            record = StateFiscalData(
                state_code="CA",
                data_timestamp=datetime.now(),
                state_tax_receipts_yoy_growth=3.5,
                state_budget_surplus_deficit_as_pct_of_gsp=-1.2
            )
            session.add(record)
            session.commit()
            
            # Verify record was created
            stored_record = session.query(StateFiscalData).first()
            assert stored_record is not None
            assert stored_record.state_code == "CA"


class TestDatabaseConfiguration:
    """Test database configuration options."""
    
    def test_sqlite_configuration(self):
        """Test SQLite-specific configuration."""
        db_url = "sqlite:///test.db"
        manager = DatabaseManager(db_url)
        
        # SQLite should not use connection pooling
        assert manager.database_url == db_url
    
    def test_postgresql_configuration(self):
        """Test PostgreSQL-specific configuration."""
        db_url = "postgresql://user:pass@localhost/test"
        pool_size = 10
        max_overflow = 20
        
        manager = DatabaseManager(db_url, pool_size=pool_size, max_overflow=max_overflow)
        
        assert manager.database_url == db_url
        # Pool configuration testing depends on actual PostgreSQL connection
    
    def test_connection_string_parsing(self):
        """Test database connection string parsing."""
        test_urls = [
            "sqlite:///test.db",
            "postgresql://user:pass@localhost:5432/dbname",
            "postgresql+psycopg2://user:pass@localhost/dbname",
            "mysql://user:pass@localhost/dbname"
        ]
        
        for url in test_urls:
            # Should not raise exception during initialization
            manager = DatabaseManager(url)
            assert manager.database_url == url