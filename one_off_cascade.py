import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("[X] DATABASE_URL no está definida en esta terminal.")
    raise SystemExit(1)

print("[i] Conectando a:", DATABASE_URL[:60] + "***")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=True)

def show_current_fk(conn):
    print("\n[i] FK actuales en 'registros':")
    rows = conn.execute(text("""
        SELECT c.conname AS name, pg_get_constraintdef(c.oid) AS definition
        FROM pg_constraint c
        JOIN pg_class rel ON rel.oid = c.conrelid
        WHERE rel.relname = 'registros' AND c.contype = 'f';
    """)).fetchall()
    if not rows:
        print("   (no hay FKs en 'registros')")
    for r in rows:
        print("  -", r.name, "=>", r.definition)

try:
    with engine.begin() as conn:
        ver = conn.execute(text("SELECT version();")).scalar()
        print("\n[i] Server version:", ver)

        show_current_fk(conn)

        print("\n[i] Modificando constraint...")
        conn.execute(text("ALTER TABLE registros DROP CONSTRAINT IF EXISTS registros_user_id_fkey;"))
        conn.execute(text("""
            ALTER TABLE registros
            ADD CONSTRAINT registros_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE;
        """))

        print("\n[i] FK tras el cambio:")
        show_current_fk(conn)

        print("\n[OK] Listo: FK de registros.user_id ahora debe tener ON DELETE CASCADE")

except SQLAlchemyError as e:
    print("[X] Error de SQLAlchemy:", e)
    raise
except Exception as e:
    print("[X] Error inesperado:", e)
    raise
