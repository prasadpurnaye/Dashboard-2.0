class Gauge:
    def __init__(self, value: float, timestamp: str, metadata: dict = None):
        if not (0 <= value <= 90):
            raise ValueError("Value must be between 0 and 90 degrees.")
        self.value = round(value, 5)
        self.timestamp = timestamp
        self.metadata = metadata if metadata is not None else {}

    def to_dict(self):
        return {
            "value": self.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }