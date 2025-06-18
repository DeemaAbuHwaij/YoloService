import os
import boto3
from .base import StorageInterface
from decimal import Decimal, InvalidOperation


class DynamoDBStorage(StorageInterface):
    def __init__(self, table_name=None, region_name="us-west-1"):
        # Determine environment and derive table suffix
        env = os.getenv("ENV", "development").lower()
        env_suffix = "prod" if env.startswith("prod") else "dev"

        # Compose full table name if not provided
        if table_name is None:
            table_name = f"deema-PolybotPredictions-{env_suffix}"

        print(f"🔧 Using DynamoDB table: {table_name} (ENV={env})")

        self.dynamodb = boto3.resource("dynamodb", region_name=region_name)
        self.table = self.dynamodb.Table(table_name)

    def save_prediction(self, request_id, original_path, predicted_path):
        print(f"📝 Saving prediction to DynamoDB: {request_id}")
        self.table.put_item(
            Item={
                "request_id": request_id,
                "type": "prediction",
                "original_path": original_path,
                "predicted_path": predicted_path
            }
        )

    def save_detection(self, request_id, label, confidence, bbox):
        print(f"📝 Saving detection to DynamoDB: {request_id}")

        def safe_decimal_list(values):
            result = []
            for v in values:
                try:
                    result.append(Decimal(str(v)))
                except (InvalidOperation, ValueError, TypeError) as e:
                    print(f"❌ Invalid bbox value: {v} — defaulting to 0. Error: {e}")
                    result.append(Decimal("0"))
            return result

        bbox_decimal = safe_decimal_list(bbox)

        self.table.put_item(
            Item={
                "request_id": f"{request_id}#{label}",
                "type": "detection",
                "label": label,
                "confidence": Decimal(str(confidence)),
                "bbox": bbox_decimal,
                "parent_id": request_id
            }
        )

    def get_prediction(self, request_id):
        response = self.table.get_item(
            Key={"request_id": request_id}
        )
        item = response.get("Item")
        if item:
            return {
                "original_path": item.get("original_path"),
                "predicted_path": item.get("predicted_path")
            }
        return None

