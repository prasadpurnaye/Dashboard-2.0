from influxdb import InfluxDBClient

class InfluxDB:
    def __init__(self, host: str, port: int, username: str, password: str, database: str):
        self.client = InfluxDBClient(host=host, port=port, username=username, password=password, database=database)

    def write_data(self, measurement: str, fields: dict, tags: dict = None):
        data = {
            "measurement": measurement,
            "tags": tags,
            "fields": fields
        }
        self.client.write_points([data])

    def read_data(self, query: str):
        result = self.client.query(query)
        return list(result.get_points())

    def close(self):
        self.client.close()