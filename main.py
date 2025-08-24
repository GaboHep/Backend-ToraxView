# main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from functools import lru_cache

from model.utils import load_model_and_transform, predict, DEVICE
from auth.routes import router as auth_router
from database import Base, engine

# Crea tablas al arrancar (Postgres)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ToraxView API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (ajusta dominios en prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # mejor: ["https://TU-FRONT.onrender.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])

# --- Root & Health: aceptar GET y HEAD para el health-check de Render ---
@app.api_route("/", methods=["GET", "HEAD"], tags=["root"])
def root():
    # Para HEAD, FastAPI/Starlette omite el body automáticamente
    return {"app": "ToraxView API", "status": "running", "docs": "/docs", "health": "/health"}

@app.api_route("/health", methods=["GET", "HEAD"], tags=["root"])
def health():
    return {"status": "ok"}

# --- CARGA PEREZOSA DEL MODELO (evita 502 por arranque pesado) ---
@lru_cache(maxsize=1)
def get_model_bundle():
    # Se ejecuta solo la primera vez que alguien llama a /predict
    model, transform, idx_to_class = load_model_and_transform()
    return model, transform, idx_to_class

@app.post("/predict", tags=["inference"])
async def predict_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    model, transform, _ = get_model_bundle()
    result = predict(image_bytes, model, transform, device=DEVICE)
    return result
