from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from ultralytics import YOLO
from PIL import Image
import os
import uuid
import shutil
import boto3
from botocore.exceptions import ClientError
from typing import Optional
import torch
import sqlite3  # Only for GET routes

# Storage
from yolo.storage.factory import get_storage  # <- adjust path if needed
storage = get_storage()

# Disable GPU usage
torch.cuda.is_available = lambda: False

app = FastAPI()

UPLOAD_DIR = "uploads/original"
PREDICTED_DIR = "uploads/predicted"
DB_PATH = "predictions.db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PREDICTED_DIR, exist_ok=True)

model = YOLO("yolov8n.pt")

labels = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard",
    "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush"
]

@app.post("/predict")
async def predict(request: Request, file: Optional[UploadFile] = File(None)):
    try:
        if "application/json" in request.headers.get("content-type", ""):
            body = await request.json()
        else:
            body = {}
    except Exception:
        body = {}

    image_name = body.get("image_name")
    chat_id = body.get("chat_id")

    uid = str(uuid.uuid4())
    ext = ".jpg"
    original_path = os.path.join(UPLOAD_DIR, uid + ext)
    predicted_path = os.path.join(PREDICTED_DIR, uid + ext)

    # Case 1: Download from S3
    if image_name and chat_id:
        bucket = os.getenv("AWS_S3_BUCKET")
        region = os.getenv("AWS_REGION")
        if not bucket:
            raise HTTPException(status_code=500, detail="❌ AWS_S3_BUCKET env var not set.")
        s3_key = f"{chat_id}/original/{image_name}"
        s3 = boto3.client("s3", region_name=region)
        try:
            s3.download_file(bucket, s3_key, original_path)
        except ClientError as e:
            raise HTTPException(status_code=400, detail=f"❌ Failed to download from S3: {e}")

    # Case 2: Direct file upload
    elif file:
        ext = os.path.splitext(file.filename)[1]
        image_name = file.filename
        chat_id = "dev-test"
        original_path = os.path.join(UPLOAD_DIR, uid + ext)
        predicted_path = os.path.join(PREDICTED_DIR, uid + ext)
        with open(original_path, "wb") as f_out:
            shutil.copyfileobj(file.file, f_out)
    else:
        raise HTTPException(status_code=400, detail="❌ No image file or image name provided.")

    print(f"🔍 Running detection on: {original_path}")
    results = model(original_path, device="cpu")
    annotated_frame = results[0].plot()
    annotated_image = Image.fromarray(annotated_frame)
    annotated_image.save(predicted_path)
    print(f"✅ Saved predicted image: {predicted_path}")

    # ✅ Save to abstract storage
    storage.save_prediction(uid, original_path, predicted_path)

    detected_labels = []
    for box in results[0].boxes:
        label_idx = int(box.cls[0].item())
        label = model.names[label_idx]
        score = float(box.conf[0])
        bbox = box.xyxy[0].tolist()
        storage.save_detection(uid, label, score, bbox)
        detected_labels.append(label)

    # ✅ Upload predicted image to S3
    if image_name and chat_id:
        try:
            bucket = os.getenv("AWS_S3_BUCKET")
            region = os.getenv("AWS_REGION")
            predicted_s3_key = f"{chat_id}/predicted/{image_name}"
            s3 = boto3.client("s3", region_name=region)
            s3.upload_file(predicted_path, bucket, predicted_s3_key)
            print(f"✅ Uploaded to s3://{bucket}/{predicted_s3_key}")
        except Exception as e:
            print(f"❌ Failed to upload predicted image: {e}")

    return {
        "prediction_uid": uid,
        "detection_count": len(results[0].boxes),
        "labels": detected_labels
    }

@app.get("/prediction/{uid}")
def get_prediction_by_uid(uid: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        session = conn.execute("SELECT * FROM prediction_sessions WHERE uid = ?", (uid,)).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Prediction not found")
        objects = conn.execute(
            "SELECT * FROM detection_objects WHERE prediction_uid = ?",
            (uid,)
        ).fetchall()
        return {
            "uid": session["uid"],
            "timestamp": session["timestamp"],
            "original_image": session["original_image"],
            "predicted_image": session["predicted_image"],
            "detection_objects": [
                {
                    "id": obj["id"],
                    "label": obj["label"],
                    "score": obj["score"],
                    "box": obj["box"]
                } for obj in objects
            ]
        }

@app.get("/predictions/label/{label}")
def get_predictions_by_label(label: str):
    normalized_label = label.strip().lower()
    normalized_labels = [l.lower() for l in labels]
    if normalized_label not in normalized_labels:
        raise HTTPException(status_code=404, detail="Invalid label")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT DISTINCT ps.uid, ps.timestamp
            FROM prediction_sessions ps
            JOIN detection_objects do ON ps.uid = do.prediction_uid
            WHERE do.label = ?
        """, (label,)).fetchall()
        return [{"uid": row["uid"], "timestamp": row["timestamp"]} for row in rows]

@app.get("/predictions/score/{min_score}")
def get_predictions_by_score(min_score: float):
    if not (0 <= min_score <= 1):
        raise HTTPException(status_code=400, detail="Score must be between 0 and 1")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT DISTINCT ps.uid, ps.timestamp
            FROM prediction_sessions ps
            JOIN detection_objects do ON ps.uid = do.prediction_uid
            WHERE do.score >= ?
        """, (min_score,)).fetchall()
        return [{"uid": row["uid"], "timestamp": row["timestamp"]} for row in rows]

@app.get("/image/{type}/{filename}")
def get_image(type: str, filename: str):
    if type not in ["original", "predicted"]:
        raise HTTPException(status_code=400, detail="Invalid image type")
    path = os.path.join("uploads", type, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)

@app.get("/prediction/{uid}/image")
def get_prediction_image(uid: str, request: Request):
    accept = request.headers.get("accept", "")
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT predicted_image FROM prediction_sessions WHERE uid = ?", (uid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Prediction not found")
        image_path = row[0]

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Predicted image file not found")

    if "image/png" in accept:
        return FileResponse(image_path, media_type="image/png")
    elif "image/jpeg" in accept or "image/jpg" in accept:
        return FileResponse(image_path, media_type="image/jpeg")
    else:
        raise HTTPException(status_code=406, detail="Client does not accept an image format")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
