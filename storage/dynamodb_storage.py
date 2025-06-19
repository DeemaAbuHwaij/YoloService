import boto3
import os
from datetime import datetime
from storage.base import Storage
import json
from decimal import Decimal
from loguru import logger


class DynamoDBStorage(Storage):
    def __init__(self):
        self.table_name = os.getenv("DYNAMODB_TABLE", "deema-PolybotPredictions-dev")
        self.region = os.getenv("AWS_REGION", "us-west-1")
        self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
        self.table = self.dynamodb.Table(self.table_name)

    def save_prediction(self, request_id, original_path, predicted_path, chat_id=None):
        logger.info("🔥 TEST LOG - inside save_prediction()")

        # Extract file names (used by Polybot to respond to user)
        original_image = os.path.basename(original_path)
        predicted_image = os.path.basename(predicted_path)

        item = {
            "request_id": str(request_id),
            "original_path": original_path,
            "predicted_path": predicted_path,
            "original_image": original_image,      # ✅ Added
            "predicted_image": predicted_image,    # ✅ Added
            "created_at": datetime.utcnow().isoformat(),
            "detections": []
        }

        if chat_id:
            item["chat_id"] = str(chat_id)

        logger.debug(f"DynamoDB put_item payload:\n{json.dumps(item, indent=2)}")
        self.table.put_item(Item=item)
        logger.info(f"[DynamoDB] Saved prediction for request_id: {request_id}")

    def save_detection(self, request_id, label, score, bbox):
        decimal_bbox = [Decimal(str(coord)) for coord in bbox]

        detection = {
            "label": label,
            "score": Decimal(str(score)),
            "bbox": decimal_bbox
        }

        self.table.update_item(
            Key={"request_id": str(request_id)},
            UpdateExpression="SET detections = list_append(if_not_exists(detections, :empty_list), :d)",
            ExpressionAttributeValues={
                ":d": [detection],
                ":empty_list": []
            }
        )
        print(f"[DynamoDB] Added detection for request_id: {request_id} -> {label} ({score:.2f})")

    def get_prediction(self, request_id):
        try:
            response = self.table.get_item(Key={'request_id': str(request_id)})
            item = response.get('Item')
            if not item:
                return None

            detections = item.get("detections", [])
            labels = [d.get("label") for d in detections if "label" in d]

            return {
                "prediction_uid": item.get("request_id"),
                "original_image": item.get("original_image"),
                "predicted_image": item.get("predicted_image"),
                "labels": labels,
                "timestamp": item.get("created_at"),
                "chat_id": item.get("chat_id")
            }
        except Exception as e:
            print(f"[ERROR] get_prediction failed: {e}")
            return None

    def get_predictions_by_score(self, min_score: float):
        min_score_decimal = Decimal(str(min_score))
        try:
            response = self.table.scan()
            items = response.get("Items", [])
            matched_predictions = []

            for item in items:
                detections = item.get("detections", [])
                for detection in detections:
                    score = Decimal(str(detection.get("score", 0)))
                    if score >= min_score_decimal:
                        matched_predictions.append({
                            "request_id": item["request_id"],
                            "timestamp": item.get("created_at")
                        })
                        break

            return matched_predictions

        except Exception as e:
            print(f"[ERROR] get_predictions_by_score failed: {e}")
            return []

    def init(self):
        pass