from __future__ import annotations

import json
from pathlib import Path

from app.repositories.garment_repository import GarmentRepository
from app.utils.file_store import FileStore
from app.utils.helpers import now_iso

COUNTRY_TO_CONTINENT = {
    "France": "Europe",
    "India": "Asia",
    "Italy": "Europe",
    "Japan": "Asia",
    "United Kingdom": "Europe",
}


class SampleDataService:
    def __init__(self, repository: GarmentRepository, file_store: FileStore, repo_root: Path) -> None:
        self.repository = repository
        self.file_store = file_store
        self.repo_root = repo_root

    def seed_from_pexels_if_needed(self) -> int:
        if self.repository.count_garments() > 0:
            return 0

        manifest_path = self.repo_root / "eval" / "sample_images" / "manifest.json"
        dataset_path = self.repo_root / "eval" / "pexels_test_set.json"
        if not manifest_path.exists() or not dataset_path.exists():
            return 0

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
        dataset_by_photo_id = {item["photo_id"]: item for item in dataset}

        imported = 0
        for row in manifest:
            source_path = self.repo_root / row["local_path"]
            if not source_path.exists():
                continue
            dataset_row = dataset_by_photo_id.get(row["photo_id"], {})
            expected = dataset_row.get("expected", {})
            copied_path = self.file_store.import_existing_file(source_path)
            description = self._build_description(row["slug"])
            ai_tags = self._build_ai_tags(expected, row["slug"])
            self.repository.save_garment(
                {
                    "image_path": str(copied_path),
                    "original_filename": copied_path.name,
                    "designer": "Pexels Sample",
                    "captured_at": None,
                    "year": None,
                    "month": None,
                    "location_hint": None,
                    "description": description,
                    "garment_type": expected.get("garment_type"),
                    "style": expected.get("style"),
                    "material": expected.get("material"),
                    "color_palette": [],
                    "pattern": None,
                    "season": None,
                    "occasion": expected.get("occasion"),
                    "consumer_profile": None,
                    "trend_notes": [row["slug"].replace("-", " ")],
                    "continent": COUNTRY_TO_CONTINENT.get(expected.get("country")),
                    "country": expected.get("country"),
                    "city": None,
                    "ai_tags": ai_tags,
                    "raw_model_output": json.dumps({"seed": True, "photo_id": row["photo_id"]}),
                    "token_estimate": 0,
                    "model_name": "seed-sample",
                    "token_source": "seed",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cached_input_tokens": 0,
                    "input_cost_usd": None,
                    "output_cost_usd": None,
                    "total_cost_usd": None,
                    "trace_id": f"seed-{row['photo_id']}",
                    "created_at": now_iso(),
                }
            )
            imported += 1
        return imported

    def _build_description(self, slug: str) -> str:
        text = slug.replace("-", " ").strip()
        if not text:
            return "Fashion sample image"
        return f"Fashion sample image showing {text}."

    def _build_ai_tags(self, expected: dict, slug: str) -> list[str]:
        tags = [
            expected.get("garment_type"),
            expected.get("style"),
            expected.get("material"),
            expected.get("occasion"),
        ]
        slug_terms = [term for term in slug.replace("-", " ").split()[:4] if term]
        combined = [tag for tag in tags if tag] + slug_terms
        unique: list[str] = []
        seen: set[str] = set()
        for item in combined:
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            unique.append(item)
        return unique
