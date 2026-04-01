from __future__ import annotations

from sqlite3 import Row

from app.data_models.full_text_search import FullTextSearchQuery
from app.repositories.database import Database
from app.utils.helpers import dump_json, load_json, now_iso


class GarmentRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def count_garments(self) -> int:
        with self.database.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM garments").fetchone()
            return int(row["count"])

    def save_garment(self, record: dict) -> int:
        payload = {
            "image_path": record["image_path"],
            "original_filename": record["original_filename"],
            "designer": record.get("designer"),
            "captured_at": record.get("captured_at"),
            "year": record.get("year"),
            "month": record.get("month"),
            "location_hint": record.get("location_hint"),
            "description": record["description"],
            "garment_type": record.get("garment_type"),
            "style": record.get("style"),
            "material": record.get("material"),
            "color_palette": record.get("color_palette", []),
            "pattern": record.get("pattern"),
            "season": record.get("season"),
            "occasion": record.get("occasion"),
            "consumer_profile": record.get("consumer_profile"),
            "trend_notes": record.get("trend_notes", []),
            "continent": record.get("continent"),
            "country": record.get("country"),
            "city": record.get("city"),
            "ai_tags": record.get("ai_tags", []),
            "raw_model_output": record.get("raw_model_output", "{}"),
            "token_estimate": record.get("token_estimate", 0),
            "model_name": record.get("model_name", ""),
            "token_source": record.get("token_source", "estimate"),
            "input_tokens": record.get("input_tokens", 0),
            "output_tokens": record.get("output_tokens", 0),
            "total_tokens": record.get("total_tokens", record.get("token_estimate", 0)),
            "cached_input_tokens": record.get("cached_input_tokens", 0),
            "input_cost_usd": record.get("input_cost_usd"),
            "output_cost_usd": record.get("output_cost_usd"),
            "total_cost_usd": record.get("total_cost_usd"),
            "trace_id": record["trace_id"],
            "created_at": record["created_at"],
        }
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO garments (
                    image_path, original_filename, designer, captured_at, year, month, location_hint,
                    description, garment_type, style, material, color_palette, pattern, season,
                    occasion, consumer_profile, trend_notes, continent, country, city, ai_tags,
                    raw_model_output, token_estimate, model_name, token_source, input_tokens,
                    output_tokens, total_tokens, cached_input_tokens, input_cost_usd, output_cost_usd,
                    total_cost_usd, trace_id, created_at
                ) VALUES (
                    :image_path, :original_filename, :designer, :captured_at, :year, :month, :location_hint,
                    :description, :garment_type, :style, :material, :color_palette, :pattern, :season,
                    :occasion, :consumer_profile, :trend_notes, :continent, :country, :city, :ai_tags,
                    :raw_model_output, :token_estimate, :model_name, :token_source, :input_tokens,
                    :output_tokens, :total_tokens, :cached_input_tokens, :input_cost_usd, :output_cost_usd,
                    :total_cost_usd, :trace_id, :created_at
                )
                """,
                {
                    **payload,
                    "color_palette": dump_json(payload["color_palette"]),
                    "trend_notes": dump_json(payload["trend_notes"]),
                    "ai_tags": dump_json(payload["ai_tags"]),
                },
            )
            garment_id = int(cursor.lastrowid)
            # Keep the FTS table in sync with the source row so search can cover
            # AI fields and later user annotations.
            self._refresh_search_document(connection, garment_id)
            return garment_id

    def get_garment(self, garment_id: int) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM garments WHERE id = ?", (garment_id,)).fetchone()
            if row is None:
                return None
            return self._row_to_dict(connection, row)

    def add_annotation(self, garment_id: int, note: str, tags: list[str]) -> None:
        with self.database.connect() as connection:
            existing = connection.execute("SELECT id FROM garments WHERE id = ?", (garment_id,)).fetchone()
            if existing is None:
                raise ValueError(f"Garment {garment_id} was not found.")
            connection.execute(
                """
                INSERT INTO annotations (garment_id, note, tags, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (garment_id, note, dump_json(tags), now_iso()),
            )
            self._refresh_search_document(connection, garment_id)

    def list_annotations(self, connection, garment_id: int) -> list[dict]:
        rows = connection.execute(
            "SELECT * FROM annotations WHERE garment_id = ? ORDER BY created_at DESC",
            (garment_id,),
        ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "note": row["note"],
                "tags": load_json(row["tags"], []),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def search(self, full_text_query: FullTextSearchQuery, filters: dict[str, str | int]) -> list[dict]:
        with self.database.connect() as connection:
            garment_ids = None
            match_query = full_text_query.sqlite_match()
            if match_query:
                # FTS narrows the candidate set first; attribute filters are
                # applied in Python after the row has been rehydrated.
                search_rows = connection.execute(
                    "SELECT garment_id FROM garment_search WHERE garment_search MATCH ?",
                    (match_query,),
                ).fetchall()
                garment_ids = {int(row["garment_id"]) for row in search_rows}
                if not garment_ids:
                    return []

            rows = connection.execute("SELECT * FROM garments ORDER BY created_at DESC").fetchall()
            results: list[dict] = []
            for row in rows:
                garment_id = int(row["id"])
                if garment_ids is not None and garment_id not in garment_ids:
                    continue
                item = self._row_to_dict(connection, row)
                if self._matches_filters(item, filters):
                    results.append(item)
            return results

    def all_garments(self) -> list[dict]:
        return self.search(FullTextSearchQuery(query=None), {})

    def list_filter_values(self) -> dict[str, list[str]]:
        rows = self.all_garments()
        return {
            "garment_type": self._collect(rows, "garment_type"),
            "style": self._collect(rows, "style"),
            "material": self._collect(rows, "material"),
            "color": self._collect_list(rows, "color_palette"),
            "pattern": self._collect(rows, "pattern"),
            "occasion": self._collect(rows, "occasion"),
            "consumer_profile": self._collect(rows, "consumer_profile"),
            "season": self._collect(rows, "season"),
            "designer": self._collect(rows, "designer"),
            "continent": self._collect_nested(rows, "location_context", "continent"),
            "country": self._collect_nested(rows, "location_context", "country"),
            "city": self._collect_nested(rows, "location_context", "city"),
            "year": self._collect(rows, "year"),
            "month": self._collect(rows, "month"),
        }

    def _matches_filters(self, item: dict, filters: dict[str, str | int]) -> bool:
        for key, expected in filters.items():
            # Color is stored as a list, so it needs list membership instead of a
            # straight scalar equality check.
            if key == "color":
                colors = {color.lower() for color in item["color_palette"]}
                if str(expected).lower() not in colors:
                    return False
                continue
            if key in {"continent", "country", "city"}:
                value = item["location_context"].get(key)
            else:
                value = item.get(key)
            if value is None:
                return False
            if str(value).lower() != str(expected).lower():
                return False
        return True

    def _refresh_search_document(self, connection, garment_id: int) -> None:
        row = connection.execute("SELECT * FROM garments WHERE id = ?", (garment_id,)).fetchone()
        if row is None:
            return
        # Flatten structured fields into a single FTS document so free-text
        # search can match descriptions, tags, annotations, and location words.
        annotations = self.list_annotations(connection, garment_id)
        trend_notes = " ".join(load_json(row["trend_notes"], []))
        ai_tags = " ".join(load_json(row["ai_tags"], []))
        annotation_text = " ".join(
            [annotation["note"] + " " + " ".join(annotation["tags"]) for annotation in annotations]
        )
        location_text = " ".join(
            [
                row["continent"] or "",
                row["country"] or "",
                row["city"] or "",
                row["location_hint"] or "",
            ]
        )
        connection.execute("DELETE FROM garment_search WHERE garment_id = ?", (garment_id,))
        connection.execute(
            """
            INSERT INTO garment_search (garment_id, description, trend_notes, ai_tags, user_annotations, location_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                garment_id,
                row["description"],
                trend_notes,
                ai_tags,
                annotation_text,
                location_text,
            ),
        )

    def _row_to_dict(self, connection, row: Row) -> dict:
        garment_id = int(row["id"])
        total_tokens = row["total_tokens"] or row["token_estimate"]
        # Convert JSON text columns back into native Python values before the
        # service layer turns them into response models.
        return {
            "id": garment_id,
            "image_path": row["image_path"],
            "original_filename": row["original_filename"],
            "designer": row["designer"],
            "captured_at": row["captured_at"],
            "year": row["year"],
            "month": row["month"],
            "description": row["description"],
            "garment_type": row["garment_type"],
            "style": row["style"],
            "material": row["material"],
            "color_palette": load_json(row["color_palette"], []),
            "pattern": row["pattern"],
            "season": row["season"],
            "occasion": row["occasion"],
            "consumer_profile": row["consumer_profile"],
            "trend_notes": load_json(row["trend_notes"], []),
            "location_context": {
                "continent": row["continent"],
                "country": row["country"],
                "city": row["city"],
            },
            "ai_tags": load_json(row["ai_tags"], []),
            "annotations": self.list_annotations(connection, garment_id),
            "token_estimate": row["token_estimate"],
            "token_usage": {
                "source": row["token_source"],
                "model_name": row["model_name"] or "",
                "token_estimate": row["token_estimate"],
                "input_tokens": row["input_tokens"],
                "output_tokens": row["output_tokens"],
                "total_tokens": total_tokens,
                "cached_input_tokens": row["cached_input_tokens"],
                "input_cost_usd": row["input_cost_usd"],
                "output_cost_usd": row["output_cost_usd"],
                "total_cost_usd": row["total_cost_usd"],
            },
            "trace_id": row["trace_id"],
            "created_at": row["created_at"],
        }

    def _collect(self, rows: list[dict], key: str) -> list[str]:
        values = {str(row[key]) for row in rows if row.get(key) not in (None, "")}
        return sorted(values)

    def _collect_list(self, rows: list[dict], key: str) -> list[str]:
        values: set[str] = set()
        for row in rows:
            values.update(str(item) for item in row.get(key, []) if item)
        return sorted(values)

    def _collect_nested(self, rows: list[dict], parent: str, key: str) -> list[str]:
        values = {
            str(row[parent][key])
            for row in rows
            if row.get(parent) and row[parent].get(key) not in (None, "")
        }
        return sorted(values)
