import os
from yolo.storage.sqlite_storage import SQLiteStorage
from yolo.storage.dynamodb_storage import DynamoDBStorage

def get_storage():
    storage_type = os.getenv("STORAGE_TYPE", "sqlite")

    if storage_type == "dynamodb":
        return DynamoDBStorage()
    else:
        return SQLiteStorage()
