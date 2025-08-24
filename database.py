# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")

# Render suele dar "postgres://"; SQLAlchemy espera "postgresql+psycopg2://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Si usas la URL EXTERNA de Render, asegúrate de que tenga ?sslmode=require
# (si ya viene con ese parámetro, no hace falta modificar aquí)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,     # reconecta si hay conexiones muertas
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
