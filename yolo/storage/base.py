# yolo/storage/base.py
from abc import ABC, abstractmethod

class StorageInterface(ABC):
    @abstractmethod
    def save_prediction(self, request_id, original_path, predicted_path):
        pass

    @abstractmethod
    def save_detection(self, request_id, label, confidence, bbox):
        pass
