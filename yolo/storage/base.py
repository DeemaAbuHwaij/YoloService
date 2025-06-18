from abc import ABC, abstractmethod

class StorageInterface(ABC):

    @abstractmethod
    def save_prediction(self, request_id: str, original_path: str, predicted_path: str):
        pass

    @abstractmethod
    def save_detection(self, request_id: str, label: str, confidence: float, bbox: str):
        pass

    @abstractmethod
    def get_prediction(self, request_id: str):
        pass
