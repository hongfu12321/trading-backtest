import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    massive_api_key: str | None
    data_dir: Path
    request_interval: float  # seconds between API calls (free tier allows ~5/min)

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        massive_api_key=os.getenv("MASSIVE_API_KEY"),
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        request_interval=float(os.getenv("MASSIVE_REQUEST_INTERVAL", "13")),
    )
