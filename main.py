# main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from model.utils import load_model_and_transform, predict, DEVICE
from auth import routes as auth_routes
from auth.routes import router as auth_router
from database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(auth_routes.router,prefix="/auth")
app.include_router(auth_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model, transform, idx_to_class = load_model_and_transform()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
async def predict_image(file: UploadFile = File(...)):
    image_bytes = await file.read()
    # OJO: pasa el device, no idx_to_class
    result = predict(image_bytes, model, transform, device=DEVICE)
    return result
