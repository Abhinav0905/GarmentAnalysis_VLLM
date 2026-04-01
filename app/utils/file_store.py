from __future__ import annotations

import shutil
from pathlib import Path

from app.utils.helpers import unique_filename


class FileStore:
    def __init__(self, upload_dir: Path) -> None:
        self.upload_dir = upload_dir

    def save_upload(self, original_name: str, content: bytes) -> Path:
        path = self.upload_dir / unique_filename(original_name)
        path.write_bytes(content)
        return path

    def import_existing_file(self, source_path: Path) -> Path:
        target_path = self.upload_dir / source_path.name
        if target_path.exists():
            target_path = self.upload_dir / unique_filename(source_path.name)
        shutil.copy2(source_path, target_path)
        return target_path

    def public_url(self, image_path: str | Path) -> str:
        name = Path(image_path).name
        return f"/uploads/{name}"
