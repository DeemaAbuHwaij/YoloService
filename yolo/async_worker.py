import os
import time
import json
import boto3
import requests
from loguru import logger
from yolo.model import predict_image
from yolo.storage.dynamodb_storage import DynamoDBStorage

# AWS clients
sqs = boto3.client("sqs", region_name=os.getenv("AWS_REGION"))
s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))

# ENV vars
QUEUE_URL = os.getenv("YOLO_SQS_QUEUE_URL")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE_NAME")
CALLBACK_BASE_URL = os.getenv("POLYBOT_CALLBACK_URL")

storage = DynamoDBStorage(table_name=DYNAMODB_TABLE)

def handle_message(body):
    request_id = body["request_id"]
    chat_id = body["chat_id"]
    bucket = body["bucket"]
    key = body["image_s3_key"]

    logger.info(f"📥 Received SQS job: {request_id}")

    local_path = f"/tmp/{request_id}.jpg"
    try:
        s3.download_file(bucket, key, local_path)
        logger.info(f"✅ Downloaded image from s3://{bucket}/{key}")
    except Exception as e:
        logger.error(f"❌ Failed to download image: {e}")
        return

    try:
        labels, bboxes, confidences, predicted_path = predict_image(local_path)
        logger.info(f"🧠 YOLO predicted labels: {labels}")
    except Exception as e:
        logger.error(f"❌ YOLO prediction failed: {e}")
        return

    # Save prediction + detections
    storage.save_prediction(request_id, f"s3://{bucket}/{key}", predicted_path)

    for label, conf, bbox in zip(labels, confidences, bboxes):
        storage.save_detection(request_id, label, conf, bbox)

    # Callback to Polybot
    try:
        callback_url = f"{CALLBACK_BASE_URL}/predictions/{request_id}"
        response = requests.post(callback_url, json={"chat_id": chat_id})
        logger.info(f"📡 Callback to {callback_url}: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Callback to Polybot failed: {e}")

def poll_queue():
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10
            )

            messages = response.get("Messages", [])
            for message in messages:
                body = json.loads(message["Body"])
                handle_message(body)

                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=message["ReceiptHandle"]
                )

        except Exception as e:
            logger.error(f"❌ Error polling SQS: {e}")

        time.sleep(1)

if __name__ == "__main__":
    logger.info("🚀 YOLO async worker started...")
    poll_queue()
