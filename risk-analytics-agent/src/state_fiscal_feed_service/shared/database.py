"""
Database connection and session management.
"""
import os
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from .models import Base
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=20,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=os.getenv("DEBUG", "false").lower() == "true"
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """Get a synchronous database session."""
        return self.SessionLocal()


# Global database manager instance
db_manager = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global db_manager
    if db_manager is None:
        from .config import get_settings
        settings = get_settings()
        db_manager = DatabaseManager(settings.database_url)
    return db_manager


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database sessions in FastAPI."""
    manager = get_database_manager()
    yield from manager.get_session()


def init_database():
    """Initialize the database (create tables)."""
    manager = get_database_manager()
    manager.create_tables()
    
    # Enable TimescaleDB extension if not already enabled
    try:
        with manager.get_session_sync() as session:
            session.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
            session.commit()
            logger.info("TimescaleDB extension enabled")
    except Exception as e:
        logger.warning(f"Could not enable TimescaleDB extension: {e}")
    
    # Create hypertable for time-series optimization
    try:
        with manager.get_session_sync() as session:
            session.execute(text(
                "SELECT create_hypertable('state_fiscal_data', 'data_timestamp', "
                "if_not_exists => TRUE);"
            ))
            session.commit()
            logger.info("TimescaleDB hypertable created")
    except Exception as e:
        logger.warning(f"Could not create TimescaleDB hypertable: {e}")