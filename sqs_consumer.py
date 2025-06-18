import boto3
import json
import os
import time
from run_yolo import run_yolo_and_store

sqs = boto3.client("sqs", region_name="us-west-1")
queue_url = os.getenv("YOLO_SQS_QUEUE_URL")

while True:
    messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1, WaitTimeSeconds=10)
    if "Messages" in messages:
        for message in messages["Messages"]:
            body = json.loads(message["Body"])
            request_id = body["request_id"]
            image_url = body["image_s3_path"]
            chat_id = body["chat_id"]

            # Download from S3, run YOLO, save to DynamoDB
            run_yolo_and_store(request_id, image_url)

            # Delete message
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
