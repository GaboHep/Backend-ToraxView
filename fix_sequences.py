# fix_sequences_v2.py
import os
from sqlalchemy import create_engine, text

def norm(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

PG_URL_RAW = os.getenv("DATABASE_URL")
if not PG_URL_RAW:
    raise SystemExit("Falta DATABASE_URL (External URL de Render con ?sslmode=require).")

engine = create_engine(norm(PG_URL_RAW), pool_pre_ping=True)

def table_exists(conn, table: str) -> bool:
    return conn.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is not None

def column_exists(conn, table: str, column: str) -> bool:
    # Busca en el esquema actual; si usas "public", puedes fijarlo en table_schema='public'
    return conn.execute(text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :t AND column_name = :c
    """), {"t": table.split(".")[-1], "c": column}).first() is not None

def get_serial_sequence_name(conn, table: str, column: str):
    return conn.execute(
        text("SELECT pg_get_serial_sequence(:t, :c)"),
        {"t": table, "c": column},
    ).scalar()

def fix_users_id_sequence():
    with engine.begin() as conn:
        if not table_exists(conn, "users"):
            print("[WARN] La tabla 'users' no existe.")
            return
        if not column_exists(conn, "users", "id"):
            print("[WARN] La columna users.id no existe.")
            return

        seq = get_serial_sequence_name(conn, "users", "id")
        if not seq:
            print("[SKIP] users.id: no tiene secuencia/identity (nada que ajustar).")
            return

        max_id = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM users")).scalar()
        conn.execute(text("SELECT setval(:seq, :val)"), {"seq": seq, "val": max_id})
        print(f"[OK] users.id: {seq} => setval({max_id})")

def check_registros_key_has_sequence():
    with engine.begin() as conn:
        if not table_exists(conn, "registros"):
            print("[WARN] La tabla 'registros' no existe.")
            return
        if not column_exists(conn, "registros", "key"):
            print("[WARN] La columna registros.key no existe.")
            return

        seq = get_serial_sequence_name(conn, "registros", "key")
        if seq:
            print(f"[INFO] registros.key tiene secuencia inesperada: {seq} (no se ajusta).")
        else:
            print("[SKIP] registros.key: sin secuencia/identity (correcto, no requiere ajuste).")

if __name__ == "__main__":
    fix_users_id_sequence()
    check_registros_key_has_sequence()
    print("[DONE] Revisión/ajuste de secuencias finalizado.")
