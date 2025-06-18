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
import threading
import json
import time
import requests

# --- Environment ---
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "sqlite").lower()
AWS_REGION = os.getenv("AWS_REGION", "us-west-1")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
POLYBOT_URL = os.getenv("POLYBOT_URL")
YOLO_URL = os.getenv("YOLO_URL", "http://localhost:8080/predict")

# --- Storage Setup ---
from storage.sqlite_storage import SQLiteStorage
from storage.dynamodb_storage import DynamoDBStorage

if STORAGE_TYPE == "dynamodb":
    storage = DynamoDBStorage()
    storage.init()
    print("📦 Using DynamoDBStorage")
else:
    db_path = os.getenv("SQLITE_DB_PATH", "predictions.db")
    storage = SQLiteStorage()
    storage.init(db_path)
    print("📦 Using SQLiteStorage")

# --- Disable GPU ---
torch.cuda.is_available = lambda: False

# --- FastAPI App ---
app = FastAPI()

UPLOAD_DIR = "uploads/original"
PREDICTED_DIR = "uploads/predicted"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PREDICTED_DIR, exist_ok=True)

model = YOLO("yolov8n.pt")

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
        if not bucket:
            raise HTTPException(status_code=500, detail="❌ AWS_S3_BUCKET not set")
        s3_key = f"{chat_id}/original/{image_name}"
        s3 = boto3.client("s3", region_name=AWS_REGION)
        try:
            s3.download_file(bucket, s3_key, original_path)
        except ClientError as e:
            raise HTTPException(status_code=400, detail=f"❌ Failed to download from S3: {e}")
    # Case 2: Direct upload
    elif file:
        ext = os.path.splitext(file.filename)[1]
        image_name = file.filename
        chat_id = "dev-test"
        with open(original_path, "wb") as f_out:
            shutil.copyfileobj(file.file, f_out)
    else:
        raise HTTPException(status_code=400, detail="❌ No image or file provided")

    print(f"🔍 Running YOLO on: {original_path}")
    results = model(original_path, device="cpu")
    annotated = Image.fromarray(results[0].plot())
    annotated.save(predicted_path)
    print(f"✅ Saved: {predicted_path}")

    # Save prediction + detections
    storage.save_prediction(uid, original_path, predicted_path, chat_id)
    detected_labels = []

    for box in results[0].boxes:
        label_idx = int(box.cls[0].item())
        label = model.names[label_idx]
        score = float(box.conf[0])
        bbox = box.xyxy[0].tolist()
        storage.save_detection(uid, label, score, bbox)
        detected_labels.append(label)

    # Upload prediction to S3
    if image_name and chat_id:
        try:
            predicted_key = f"{chat_id}/predicted/{image_name}"
            s3 = boto3.client("s3", region_name=AWS_REGION)
            s3.upload_file(predicted_path, os.getenv("AWS_S3_BUCKET"), predicted_key)
            print(f"📤 Uploaded to S3: {predicted_key}")
        except Exception as e:
            print(f"❌ Upload failed: {e}")

    # Notify Polybot
    if POLYBOT_URL:
        try:
            callback_url = f"{POLYBOT_URL}/predictions/{uid}"
            print(f"📡 Notifying Polybot: {callback_url}")
            r = requests.post(callback_url)
            if r.status_code != 200:
                print(f"⚠️ Polybot error: {r.status_code}")
        except Exception as e:
            print(f"❌ Failed to notify Polybot: {e}")

    return {
        "prediction_uid": uid,
        "detection_count": len(detected_labels),
        "labels": detected_labels
    }

@app.get("/predictions/{uid}")
def get_prediction(uid: str):
    result = storage.get_prediction(uid)
    if not result:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return result

@app.get("/predictions/score/{min_score}")
def get_predictions_by_score(min_score: float):
    if not (0 <= min_score <= 1):
        raise HTTPException(status_code=400, detail="Score must be between 0 and 1")
    return storage.get_predictions_by_score(min_score)

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
    prediction = storage.get_prediction(uid)
    if not prediction or not prediction.get("predicted_path"):
        raise HTTPException(status_code=404, detail="Prediction or image not found")
    image_path = prediction["predicted_path"]
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Predicted image not found")

    accept = request.headers.get("accept", "")
    if "image/png" in accept:
        return FileResponse(image_path, media_type="image/png")
    elif "image/jpeg" in accept or "image/jpg" in accept:
        return FileResponse(image_path, media_type="image/jpeg")
    else:
        raise HTTPException(status_code=406, detail="Unsupported format requested")

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.2"}

# --- SQS Background Consumer ---
def consume_messages():
    if not SQS_QUEUE_URL:
        print("⚠️ No SQS_QUEUE_URL set — skipping consumer")
        return

    sqs = boto3.client("sqs", region_name=AWS_REGION)
    print(f"🟢 Listening to SQS queue: {SQS_QUEUE_URL}")
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=10
            )
            messages = response.get("Messages", [])
            if not messages:
                time.sleep(1)
                continue

            for msg in messages:
                body = json.loads(msg["Body"])
                print(f"📥 Received: {body}")
                try:
                    requests.post(YOLO_URL, json=body)
                except Exception as e:
                    print(f"❌ Failed to process image: {e}")

                sqs.delete_message(
                    QueueUrl=SQS_QUEUE_URL,
                    ReceiptHandle=msg["ReceiptHandle"]
                )
                print("🗑️ Deleted from SQS")

        except Exception as e:
            print(f"❌ SQS error: {e}")
            time.sleep(5)

@app.on_event("startup")
def start_consumer_thread():
    t = threading.Thread(target=consume_messages, daemon=True)
    t.start()

# --- Run App ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
