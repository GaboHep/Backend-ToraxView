# one_off_cascade.py
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Falta DATABASE_URL. Ej: export DATABASE_URL='postgresql+psycopg://USER:PASS@HOST:5432/DB?sslmode=require'")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# OJO: el constraint se llama así según tu error: registros_user_id_fkey
sql = """
ALTER TABLE registros DROP CONSTRAINT IF EXISTS registros_user_id_fkey;
ALTER TABLE registros
ADD CONSTRAINT registros_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id)
ON DELETE CASCADE;
"""

with engine.begin() as conn:
    for stmt in sql.strip().split(";"):
        s = stmt.strip()
        if s:
            conn.execute(text(s))

print("Listo: FK de registros.user_id ahora es ON DELETE CASCADE")
