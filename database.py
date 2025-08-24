# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Lee la URL desde el entorno; en local puedes seguir usando SQLite si quieres.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")

# Render suele entregar "postgres://...".
# Para SQLAlchemy + psycopg3 queremos "postgresql+psycopg://..."
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Si usas la External URL de Render desde tu máquina, asegúrate de incluir ?sslmode=require en la variable de entorno.
# (Con la Internal URL de Render no es necesario porque va por red privada.)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # reconecta si la conexión está muerta
    pool_recycle=1800,    # recicla conexiones cada 30 min para evitar timeouts del proveedor
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
