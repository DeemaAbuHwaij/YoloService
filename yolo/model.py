from ultralytics import YOLO
from PIL import Image
import os
import torch

# Disable GPU for EC2 CPU-based inference
torch.cuda.is_available = lambda: False
model = YOLO("yolov8n.pt")

def predict_image(image_path):
    results = model(image_path, device="cpu")
    annotated_frame = results[0].plot()
    annotated_image = Image.fromarray(annotated_frame)

    predicted_path = image_path.replace("original", "predicted")
    os.makedirs(os.path.dirname(predicted_path), exist_ok=True)
    annotated_image.save(predicted_path)

    labels, boxes, confidences = [], [], []

    for box in results[0].boxes:
        label_idx = int(box.cls[0].item())
        label = model.names[label_idx]
        labels.append(label)
        confidences.append(float(box.conf[0]))
        boxes.append(box.xyxy[0].tolist())

    return labels, boxes, confidences, predicted_path
