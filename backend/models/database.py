"""Database Configuration and Models

SQLAlchemy setup with PostgreSQL/TimescaleDB for storing events.
Provides session management and declarative base for models.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://flashpoint:flashpoint@localhost:5432/flashpoint")

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ========== MODELS ==========

class Event(Base):
    """Intelligence event from any source"""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False, index=True)
    text = Column(Text, nullable=False)
    url = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    bias = Column(String(50))
    
    # Content hash for deduplication
    content_hash = Column(String(64), unique=True, index=True)
    
    # Extracted metadata
    entities = Column(JSON)  # {locations: [], organizations: [], persons: []}
    sentiment = Column(Float)  # -1 to 1
    
    # Vector embedding ID (stored in Qdrant)
    embedding_id = Column(String(100))
    
    # Geographic data
    lat = Column(Float)
    lon = Column(Float)
    place = Column(String(200))
    
    # Indexes for time-series queries
    __table_args__ = (
        Index('idx_timestamp_source', 'timestamp', 'source'),
        Index('idx_bias_timestamp', 'bias', 'timestamp'),
    )


class Commodity(Base):
    """Commodity price tracking"""
    __tablename__ = "commodities"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    name = Column(String(100))
    rate = Column(Float, nullable=False)
    unit = Column(String(10), default="USD")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    change_24h = Column(Float)
    
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
    )


class Conflict(Base):
    """Conflict tracking from CFR"""
    __tablename__ = "conflicts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    status = Column(String(50))  # Worsening, Unchanging, Improving
    impact = Column(String(50))  # Critical, Significant, Limited
    severity = Column(Integer)  # 1-10
    description = Column(Text)
    
    lat = Column(Float)
    lon = Column(Float)
    region = Column(String(100))
    
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_impact_severity', 'impact', 'severity'),
    )


# ========== DATABASE UTILITIES ==========

def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")


def init_timescaledb():
    """Convert events table to TimescaleDB hypertable"""
    try:
        with engine.connect() as conn:
            # Check if TimescaleDB extension exists
            conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            
            # Convert events table to hypertable
            conn.execute("""
                SELECT create_hypertable('events', 'timestamp', 
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                );
            """)
            
            # Convert commodities table to hypertable
            conn.execute("""
                SELECT create_hypertable('commodities', 'timestamp',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 hour'
                );
            """)
            
            print("✅ TimescaleDB hypertables configured")
    except Exception as e:
        print(f"⚠️ TimescaleDB setup skipped (requires extension): {e}")
