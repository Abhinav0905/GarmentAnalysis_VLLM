from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    app_name: str
    host: str
    port: int
    model_provider: str
    seed_sample_data: bool
    openai_api_key: str
    openai_model: str
    openai_timeout_seconds: int
    openai_input_cost_per_million: float | None
    openai_cached_input_cost_per_million: float | None
    openai_output_cost_per_million: float | None
    max_upload_size_mb: int
    data_dir: Path
    upload_dir: Path
    database_path: Path
    trace_log_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        # Load .env first so local development works without manual export
        # commands. Existing shell variables still win.
        load_dotenv_file()
        data_dir = Path(os.getenv("DATA_DIR", "data")).resolve()
        return cls(
            app_name=os.getenv("APP_NAME", "Fashion Inspiration Library"),
            host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "8000")),
            model_provider=os.getenv("MODEL_PROVIDER", "mock").lower(),
            seed_sample_data=os.getenv("SEED_SAMPLE_DATA", "true").lower() == "true",
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            openai_timeout_seconds=int(os.getenv("OPENAI_TIMEOUT_SECONDS", "60")),
            openai_input_cost_per_million=_optional_float_env("OPENAI_INPUT_COST_PER_MILLION"),
            openai_cached_input_cost_per_million=_optional_float_env("OPENAI_CACHED_INPUT_COST_PER_MILLION"),
            openai_output_cost_per_million=_optional_float_env("OPENAI_OUTPUT_COST_PER_MILLION"),
            max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")),
            data_dir=data_dir,
            upload_dir=data_dir / "uploads",
            database_path=data_dir / "fashion.db",
            trace_log_path=data_dir / "traces.jsonl",
        )

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.trace_log_path.parent.mkdir(parents=True, exist_ok=True)


def load_dotenv_file(dotenv_path: str = ".env") -> None:
    path = Path(dotenv_path)
    if not path.exists():
        return

    # Keep the parser intentionally tiny: KEY=value lines, optional quotes, and
    # comments. That is enough for this project without another dependency.
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def _optional_float_env(name: str) -> float | None:
    raw_value = os.getenv(name)
    if raw_value in (None, ""):
        return None
    return float(raw_value)
