from __future__ import annotations

import json
import subprocess
from pathlib import Path

DATASET_PATH = Path(__file__).with_name("pexels_test_set.json")
OUTPUT_DIR = Path(__file__).with_name("sample_images")
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


def optimized_image_url(base_url: str) -> str:
    # Use a resized Pexels image so the repo keeps a practical local sample set.
    return f"{base_url}?auto=compress&cs=tinysrgb&w=600"


def download_file(url: str, target_path: Path) -> None:
    subprocess.run(
        ["curl", "-Ls", "--retry", "2", url, "-o", str(target_path)],
        check=True,
    )


def slugify(value: str) -> str:
    return "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in value)


def main() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # The dataset currently contains some duplicate URLs for the same Pexels photo
    # id, so keep only the first copy when downloading local samples.
    unique_items: list[dict] = []
    seen_photo_ids: set[str] = set()
    for item in dataset:
        if item["photo_id"] in seen_photo_ids:
            continue
        seen_photo_ids.add(item["photo_id"])
        unique_items.append(item)

    manifest: list[dict] = []
    for item in unique_items:
        suffix = Path(item["image_url"]).suffix or ".jpg"
        filename = f"{item['photo_id']}-{slugify(item['slug'])}{suffix}"
        target_path = OUTPUT_DIR / filename
        source_url = optimized_image_url(item["image_url"])

        if not target_path.exists():
            download_file(source_url, target_path)

        manifest.append(
            {
                "id": item["id"],
                "photo_id": item["photo_id"],
                "slug": item["slug"],
                "source_page": "https://www.pexels.com/search/fashion/",
                "source_image_url": item["image_url"],
                "downloaded_image_url": source_url,
                "local_path": str(target_path.relative_to(Path.cwd())),
            }
        )

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Downloaded {len(manifest)} images into {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
