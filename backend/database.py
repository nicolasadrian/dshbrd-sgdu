import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Configuración del motor de Base de Datos principal
def get_engine():
    db_url = os.getenv("DATABASE_URL_LOCAL") or os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_PUBLIC")
    if not db_url:
        db_url = "postgresql://postgres:lenovo@localhost:5432/sade_db"
    
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    return create_engine(
        db_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_timeout=30,
        connect_args={"options": "-c statement_timeout=30000"},
    )

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Configuración del motor secundario geo-mdr
def get_geo_mdr_engine():
    db_url = os.getenv("DATABASE_URL_LOCAL") or os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_PUBLIC")
    if not db_url:
        db_url = "postgresql://postgres:lenovo@localhost:5432/sade_db"
    
    base_url, _ = db_url.rsplit('/', 1)
    geo_url = f"{base_url}/geo-mdr"
    
    if geo_url.startswith("postgres://"):
        geo_url = geo_url.replace("postgres://", "postgresql://", 1)
        
    return create_engine(
        geo_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_timeout=30,
    )

geo_engine = get_geo_mdr_engine()

# Dependencia para inyectar sesión de SQLAlchemy en FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
