import boto3
from decimal import Decimal, InvalidOperation
from .base import StorageInterface  # Optional if you use a common interface

class DynamoDBStorage(StorageInterface):
    def __init__(self, table_name=None, region_name="us-west-1"):
        if not table_name:
            table_name = os.getenv("DYNAMODB_TABLE_NAME")
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

        def safe_decimal(value):
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError, TypeError):
                return Decimal(0)

        def safe_decimal_list(values):
            return [safe_decimal(v) for v in values]

        self.table.put_item(
            Item={
                "request_id": f"{request_id}#{label}",
                "type": "detection",
                "label": label,
                "confidence": safe_decimal(confidence),
                "bbox": safe_decimal_list(bbox),
                "parent_id": request_id
            }
        )
