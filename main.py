# main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

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

# Root y health
@app.get("/", tags=["root"])
def root():
    return {
        "app": "ToraxView API",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", tags=["root"])
def health():
    return {"status": "ok"}

# Carga del modelo (como lo tenías)
model, transform, idx_to_class = load_model_and_transform()

@app.post("/predict", tags=["inference"])
async def predict_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = predict(image_bytes, model, transform, device=DEVICE)
    return result
