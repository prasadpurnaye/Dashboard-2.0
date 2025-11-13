from pydantic import BaseSettings

class Settings(BaseSettings):
    influxdb_url: str
    influxdb_token: str
    influxdb_org: str
    influxdb_bucket: str

    class Config:
        env_file = ".env"

settings = Settings()