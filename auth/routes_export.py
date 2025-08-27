# auth/routes_export.py
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional, List
import io, csv, json, os, zipfile, base64, re

# Ajusta estos imports a tu proyecto
from auth.auth_utils import get_db, get_current_admin_user
from .models import Registro, User  # Asegúrate de tener la relación Registro.user (opcional)

router = APIRouter(prefix="/export", tags=["export"])

def _make_filename(prefix: str, user_id, date_from, date_to, ext: str):
    parts = [prefix]
    if user_id: parts.append(f"user{user_id}")
    if date_from: parts.append(f"from{date_from.isoformat()}")
    if date_to: parts.append(f"to{date_to.isoformat()}")
    parts.append(datetime.now().strftime("%Y%m%d_%H%M%S"))
    return "_".join(parts) + f".{ext}"

def _build_query(db: Session, user_id: Optional[int], date_from: Optional[date], date_to: Optional[date]):
    q = db.query(Registro)
    # Si tienes relación con User:
    # q = q.join(User, Registro.user_id == User.id, isouter=True)
    if user_id:
        q = q.filter(Registro.user_id == user_id)
    if date_from:
        q = q.filter(Registro.inference_date >= date_from)
    if date_to:
        q = q.filter(Registro.inference_date <= date_to)
    return q.order_by(Registro.inference_date.desc(), Registro.key.desc())

def _resultados_to_string(resultados):
    # Tu columna suele ser TEXT con JSON.stringify, pero soporta JSONB
    if isinstance(resultados, str):
        return resultados
    try:
        return json.dumps(resultados, ensure_ascii=False)
    except Exception:
        return str(resultados or "[]")

def _registro_to_row(r: Registro):
    return {
        "key": r.key,
        "inference_date": getattr(r.inference_date, "isoformat", lambda: r.inference_date)(),
        "birth_date": getattr(r.birth_date, "isoformat", lambda: r.birth_date)(),
        "gender": r.gender,
        "city": r.city,
        "parish": r.parish,
        "province": getattr(r, "canton", None),
        "feedback": r.feedback or "",
        "resultados": _resultados_to_string(getattr(r, "resultados", "[]")),
        "image_path": getattr(r, "image_path", None),   # si guardas en disco
        "image": getattr(r, "image", None),             # si guardas DataURL/base64 en DB
    }

def _dataurl_to_bytes(dataurl: str) -> bytes:
    # Convierte DataURL a bytes (para incluir en ZIP)
    # e.g. data:image/png;base64,AAAA...
    if not dataurl:
        return b""
    if dataurl.startswith("data:"):
        base64_part = dataurl.split(",", 1)[1]
        return base64.b64decode(base64_part)
    # si te guardaron solo el base64 pelado:
    return base64.b64decode(dataurl)

@router.get("/registros")
def export_registros(
    user_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    format: str = Query("csv", pattern="^(csv|json|zip)$"),
    include_images: bool = Query(False),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    rows: List[Registro] = _build_query(db, user_id, date_from, date_to).all()

    # JSON
    if format == "json":
        data = [_registro_to_row(r) for r in rows]
        filename = _make_filename("registros", user_id, date_from, date_to, "json")
        return JSONResponse(content=data, headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        })

    # CSV
    if format == "csv":
        filename = _make_filename("registros", user_id, date_from, date_to, "csv")
        output = io.StringIO()
        fieldnames = [
            "key","inference_date","birth_date","gender","city","parish","province",
            "feedback","resultados","image_path","image"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(_registro_to_row(r))
        resp = PlainTextResponse(content=output.getvalue(), media_type="text/csv")
        resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

    # ZIP (CSV + imágenes opcionales)
    filename = _make_filename("registros", user_id, date_from, date_to, "zip")
    memfile = io.BytesIO()
    with zipfile.ZipFile(memfile, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # CSV dentro del ZIP
        csv_buf = io.StringIO()
        fieldnames = [
            "key","inference_date","birth_date","gender","city","parish","province",
            "feedback","resultados","image_path","image"
        ]
        writer = csv.DictWriter(csv_buf, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(_registro_to_row(r))
        zf.writestr("registros.csv", csv_buf.getvalue())

        if include_images:
            for r in rows:
                # 1) Si tienes ruta en disco
                image_path = getattr(r, "image_path", None)
                if image_path and os.path.isfile(image_path):
                    try:
                        with open(image_path, "rb") as f:
                            zf.writestr(f"images/{os.path.basename(image_path)}", f.read())
                        continue
                    except Exception:
                        pass
                # 2) Si la DB guarda DataURL/base64 en campo 'image'
                image_data = getattr(r, "image", None)
                if image_data:
                    try:
                        raw = _dataurl_to_bytes(image_data)
                        zf.writestr(f"images/{r.key}.png", raw)
                    except Exception:
                        pass

    memfile.seek(0)
    return StreamingResponse(memfile, media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="{filename}"'
    })
