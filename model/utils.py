# utils.py

import os
import io
import cv2
import torch
import numpy as np
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

# === CLASES (mismo orden que en entrenamiento) ===
CLASSES = [
    'Atelectasis', 'Cardiomegaly', 'Effusion', 'Infiltration', 'Mass',
    'Nodule', 'Pneumonia', 'Pneumothorax', 'No Finding', 'Tuberculosis',
    'Emphysema', 'Fibrosis', 'Pleural_Thickening'
]
NUM_CLASSES = len(CLASSES)

MODEL_PATH = "model/model.pth"  # coloca aquí tu MODELOPORCLASEDensenet-Combinada-prepo.pth

# Dispositivo global para usarlo en predict()
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def build_model(num_labels: int) -> nn.Module:
    """
    Construye EXACTAMENTE la arquitectura usada en entrenamiento:
    DenseNet121 + Linear(in_features, num_labels)
    """
    model = models.densenet121(weights=None)  # no uses pesos IMAGENET al cargar un state_dict
    in_feats = model.classifier.in_features
    model.classifier = nn.Linear(in_feats, num_labels)
    return model

def safe_load_state_dict(model: nn.Module, path: str, map_location):
    """
    Carga segura del state_dict. Usa weights_only=True si está disponible
    y hace fallback si no.
    """
    try:
        state = torch.load(path, map_location=map_location, weights_only=True)  # PyTorch >= 2.4
    except TypeError:
        state = torch.load(path, map_location=map_location)  # fallback versiones previas
    model.load_state_dict(state, strict=True)

def load_model_and_transform():
    """
    Mantiene la misma firma que usas en main.py:
    return model, transform, idx_to_class
    """
    model = build_model(NUM_CLASSES)
    safe_load_state_dict(model, MODEL_PATH, map_location=DEVICE)
    model.to(DEVICE).eval()

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
    ])

    # idx_to_class para quien lo necesite en la API
    idx_to_class = {i: c for i, c in enumerate(CLASSES)}
    return model, transform, idx_to_class

def apply_clahe(img_pil: Image.Image) -> Image.Image:
    # Mantén el preprocesamiento como lo tenías
    img = img_pil.convert("RGB").resize((224, 224))
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    img_clahe = clahe.apply(img_cv)
    img_rgb = cv2.cvtColor(img_clahe, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(img_rgb)

def predict(image_bytes: bytes, model: nn.Module, transform, device=None):
    device = device or DEVICE
    image = Image.open(io.BytesIO(image_bytes))
    image = apply_clahe(image)
    tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probs = torch.sigmoid(logits).cpu().numpy()[0]

    result = [{"label": CLASSES[i], "probability": float(p)} for i, p in enumerate(probs)]
    result.sort(key=lambda x: x["probability"], reverse=True)

    precision_general = float(np.mean(probs))  # tu métrica agregada actual

    return {
        "predictions": result,
        "precision": precision_general
    }
