def format_gauge_value(value):
    if value < 0 or value > 90:
        raise ValueError("Value must be between 0 and 90 degrees.")
    return f"{value:.5f}"

def validate_gauge_data(data):
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary.")
    required_keys = ['value', 'timestamp']
    for key in required_keys:
        if key not in data:
            raise KeyError(f"Missing required key: {key}")
    if not (0 <= data['value'] <= 90):
        raise ValueError("Gauge value must be between 0 and 90 degrees.")
    return True

def calculate_average(values):
    if not values:
        return 0.0
    return sum(values) / len(values)