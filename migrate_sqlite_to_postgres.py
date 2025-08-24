# migrate_sqlite_to_postgres.py
"""
Migra usuarios y registros desde SQLite (local) a PostgreSQL (Render).

- Preserva los IDs para no romper claves foráneas (asume DB de destino vacía).
- Evita duplicados por id/username.
- Soporta psycopg3 (SQLAlchemy URL: postgresql+psycopg://...)
- Si no puedes importar el modelo 'Registro', hace copia por reflexión de la tabla 'registros'.

Variables de entorno requeridas:
  SQLITE_URL    -> ej. sqlite:///C:/ruta/a/users.db  (en Windows usa / y no \)
  DATABASE_URL  -> External URL de Render con ?sslmode=require
"""

import os
from typing import Optional, Dict, Any, Iterable

from sqlalchemy import create_engine, select, MetaData, Table
from sqlalchemy.orm import sessionmaker

# --- Normaliza la URL de Postgres a psycopg3 ---
def normalize_pg_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url

SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:///./users.db")
PG_URL_RAW = os.getenv("DATABASE_URL")
if not PG_URL_RAW:
    raise SystemExit("Falta DATABASE_URL (External URL de Render, con ?sslmode=require).")
PG_URL = normalize_pg_url(PG_URL_RAW)

print(f"[INFO] SQLITE_URL = {SQLITE_URL}")
print(f"[INFO] POSTGRES_URL = {PG_URL}")

# Motores / sesiones
src_engine = create_engine(SQLITE_URL)
dst_engine = create_engine(PG_URL, pool_pre_ping=True)

SrcSession = sessionmaker(bind=src_engine)
DstSession = sessionmaker(bind=dst_engine)

# --- Importa modelos ORM si existen ---
User = None
Registro = None
try:
    # Ajusta si tu User está en otro módulo
    from auth.models import User as _User
    User = _User
    print("[INFO] Modelo User importado desde auth.models")
except Exception as e:
    print(f"[WARN] No se pudo importar User desde auth.models: {e}")

# Intentos comunes para Registro; ajusta si lo tienes en otro sitio
for path in ("registros.models", "auth.models", "models"):
    if Registro:
        break
    try:
        mod = __import__(path, fromlist=["Registro"])
        if hasattr(mod, "Registro"):
            Registro = getattr(mod, "Registro")
            print(f"[INFO] Modelo Registro importado desde {path}")
    except Exception:
        pass

# --- Utilidades ---
def chunked(iterable: Iterable, size: int):
    buf = []
    for x in iterable:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

def copy_users():
    if User is None:
        print("[ERROR] No se pudo importar el modelo User. Aborta migración de usuarios.")
        return 0

    inserted = 0
    with SrcSession() as ssrc, DstSession() as sdst:
        src_users = ssrc.query(User).all()
        print(f"[INFO] Usuarios a migrar: {len(src_users)}")

        for batch in chunked(src_users, 200):
            for u in batch:
                # evita duplicar por id o username
                if sdst.query(User).filter_by(id=u.id).first():
                    continue
                if sdst.query(User).filter_by(username=u.username).first():
                    continue

                # Ajusta campos si tu modelo tiene más/menos columnas
                new_u = User(
                    id=u.id,
                    username=u.username,
                    hashed_password=u.hashed_password,
                    role=getattr(u, "role", "usuario"),
                )
                sdst.add(new_u)
            sdst.commit()
            inserted += len(batch)
    return inserted

def copy_registros():
    """
    Copia por ORM si hay modelo Registro; de lo contrario usa reflexión de tabla 'registros'.
    """
    inserted = 0

    if Registro is not None:
        with SrcSession() as ssrc, DstSession() as sdst:
            src_regs = ssrc.query(Registro).all()
            print(f"[INFO] Registros a migrar (ORM): {len(src_regs)}")

            for batch in chunked(src_regs, 200):
                for r in batch:
                    # Evita duplicados por clave natural si existe; si no, por id
                    # Ajusta la 'key' si tu modelo tiene un identificador natural
                    if hasattr(Registro, "key") and getattr(r, "key", None) is not None:
                        if sdst.query(Registro).filter_by(key=r.key).first():
                            continue
                    else:
                        if sdst.query(Registro).filter_by(id=r.id).first():
                            continue

                    # Crea el nuevo objeto preservando IDs
                    args: Dict[str, Any] = r.__dict__.copy()
                    args.pop("_sa_instance_state", None)
                    obj = Registro(**args)
                    sdst.add(obj)
                sdst.commit()
                inserted += len(batch)
        return inserted

    # --- Reflexión si no hay modelo Registro ---
    print("[WARN] No se pudo importar Registro; intentaremos copia por reflexión de tabla 'registros'.")
    src_meta = MetaData()
    dst_meta = MetaData()
    try:
        src_tbl = Table("registros", src_meta, autoload_with=src_engine)
        dst_tbl = Table("registros", dst_meta, autoload_with=dst_engine)
    except Exception as e:
        print(f"[ERROR] No se pudo reflejar la tabla 'registros': {e}")
        return 0

    with src_engine.connect() as csrc, dst_engine.begin() as cdst:
        rows = csrc.execute(select(src_tbl)).fetchall()
        print(f"[INFO] Registros a migrar (reflexión): {len(rows)}")

        # Inserta en lotes
        for batch in chunked(rows, 200):
            payload = []
            for row in batch:
                data = dict(row._mapping)
                payload.append(data)
            if payload:
                cdst.execute(dst_tbl.insert(), payload)
            inserted += len(batch)
    return inserted


def main():
    print("[INFO] Iniciando migración...")
    users = copy_users()
    regs = copy_registros()
    print(f"[DONE] Usuarios migrados (procesados por lotes): {users}")
    print(f"[DONE] Registros migrados (procesados por lotes): {regs}")
    print("[INFO] Migración completa.")

if __name__ == "__main__":
    main()
