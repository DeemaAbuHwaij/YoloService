import os
import requests
import boto3
from ultralytics import YOLO
from PIL import Image
import uuid
from io import BytesIO
from yolo.storage.dynamodb_storage import DynamoDBStorage  # Make sure this path is correct

s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
model = YOLO("yolov8n.pt")

def run_yolo_and_store(request_id, s3_url, chat_id):
    print(f"📥 Downloading image from {s3_url}")
    bucket_name = os.getenv("S3_BUCKET_NAME")
    key = s3_url.split(f"{bucket_name}/")[-1]

    image_bytes = s3.get_object(Bucket=bucket_name, Key=key)['Body'].read()
    image = Image.open(BytesIO(image_bytes))

    results = model.predict(image, save=False)
    result = results[0]

    storage = DynamoDBStorage()
    storage.save_prediction(request_id, s3_url, s3_url)  # For now, use s3_url as both paths

    for box in result.boxes:
        label = result.names[int(box.cls)]
        confidence = float(box.conf)
        bbox = box.xyxy[0].tolist()
        storage.save_detection(request_id, label, confidence, bbox)

    callback_url = f"{os.getenv('POLYBOT_CALLBACK_URL')}/predictions/{request_id}"
    print(f"🔁 Sending callback to {callback_url}")
    requests.post(callback_url, json={"chat_id": chat_id})
