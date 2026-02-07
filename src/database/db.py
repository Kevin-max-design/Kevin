"""
Database Connection and Session Management

Provides database initialization and session handling.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from .models import Base


class Database:
    """Database connection manager."""
    
    def __init__(self, db_path: str = "data/jobs.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def init_db(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """Get a database session with automatic cleanup.
        
        Usage:
            with db.get_session() as session:
                session.add(job)
                session.commit()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_db(self) -> Session:
        """Get a database session (for FastAPI dependency injection)."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()


# Global database instance
_db: Database = None


def get_database(db_path: str = "data/jobs.db") -> Database:
    """Get or create the global database instance."""
    global _db
    if _db is None:
        _db = Database(db_path)
        _db.init_db()
    return _db
