# auth/routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Quita esta línea (ya no se usa):
# from database import SessionLocal

from .models import User, Registro
from .schemas import UserLogin, RegistroCreate

# Trae get_db y utilidades SOLO desde auth_utils (fuente única)
from auth.auth_utils import (
    get_db,
    get_current_admin_user,
    get_current_user,
    hash_password,
    verify_password,
    create_access_token,
)

from auth.schemas import RadiologoCreate, RadiologoOut, RadiologoUpdate

router = APIRouter()

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    token = create_access_token({"sub": db_user.username, "role": db_user.role})
    return {"access_token": token, "role": db_user.role}

## ELEMENTOS PARA EL CRUD DE USUARIOS CON PROTECCIÓN PARA SOLO USO POR ROL ADMIN

@router.get("/radiologos", response_model=list[RadiologoOut])
def get_radiologos(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    return db.query(User).filter(User.role == "radiologo").all()

@router.post("/radiologos", response_model=RadiologoOut)
def create_radiologo(radiologo: RadiologoCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    existing_user = db.query(User).filter(User.username == radiologo.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    nuevo = User(
        username=radiologo.username,
        hashed_password=hash_password(radiologo.password),
        role="radiologo"
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.put("/radiologos/{id}", response_model=RadiologoOut)
def update_radiologo(id: int, data: RadiologoUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    rad = db.query(User).filter(User.id == id, User.role == "radiologo").first()
    if not rad:
        raise HTTPException(status_code=404, detail="Radiologo no encontrado")
    rad.username = data.username
    rad.hashed_password = hash_password(data.password)
    db.commit()
    db.refresh(rad)
    return rad

@router.delete("/radiologos/{id}")
def delete_radiologo(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    rad = db.query(User).filter(User.id == id, User.role == "radiologo").first()
    if not rad:
        raise HTTPException(status_code=404, detail="Radiologo no encontrado")
    db.delete(rad)
    db.commit()
    return {"msg": "Radiologo eliminado correctamente"}


##Endpoint para guardar registro de inferencia / resultados

@router.post("/guardar_registro")
def guardar_registro(data: RegistroCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    existe = db.query(Registro).filter_by(key=data.key).first()
    if existe:
        raise HTTPException(status_code=400, detail="Registro ya existe")

    nuevo = Registro(
        key=data.key,
        user_id=current_user.id,
        inference_date=data.inference_date,
        birth_date=data.birth_date,
        gender=data.gender,
        city=data.city,
        parish=data.parish,
        canton=data.canton,
        precision=data.precision,
        resultados=data.resultados,
        feedback=data.feedback,
        image=data.image,
    )
    db.add(nuevo)
    db.commit()
    return {"msg": "Registro guardado"}

@router.get("/mis_registros")
def mis_registros(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    registros = db.query(Registro).filter_by(user_id=current_user.id).all()
    return registros

@router.get("/registros_por_radiologo/{radiologo_id}")
def registros_por_radiologo(radiologo_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    registros = db.query(Registro).filter(Registro.user_id == radiologo_id).order_by(Registro.inference_date.desc()).all()
    return registros
