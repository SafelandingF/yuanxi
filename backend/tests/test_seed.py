"""Shared catalog validation and non-destructive SQLite import."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from backend.domain.matching import search_candidates
from backend.domain.schemas import Preferences, Profile
from backend.infrastructure.seed import DATASET_PATH, seed_candidates
from backend.infrastructure.sqlite import Store


class SeedTests(unittest.TestCase):
    def test_shared_catalog_is_diverse_and_searchable(self):
        rows = seed_candidates()
        self.assertEqual(len(rows), 1200)
        self.assertEqual(len({c["id"] for c in rows}), 1200)
        self.assertEqual(len({c["city"] for c in rows}), 20)
        self.assertEqual(
            (min(c["age"] for c in rows), max(c["age"] for c in rows)), (18, 60)
        )
        profile = Profile(
            name="测试",
            age=35,
            city="深圳",
            goal="认真长久",
            rhythm="规律慢生活",
            interests=["阅读"],
            companionship="每周 1 次",
        )
        result = search_candidates(
            profile.model_dump(),
            Preferences(city="深圳", age_min=30, age_max=50).model_dump(),
            rows,
            [],
            False,
        )
        self.assertGreater(result["matched"], 3)
        self.assertEqual(len(result["candidates"]), 3)
        self.assertTrue(
            all(
                c["city"] == "深圳" and 30 <= c["age"] <= 50
                for c in result["candidates"]
            )
        )

    def test_upgrade_preserves_existing_records_and_is_repeatable(self):
        rows = seed_candidates()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.db"
            with patch(
                "backend.infrastructure.sqlite.seed_candidates", return_value=rows[:120]
            ):
                old = Store(path)
            old.save("private-session", {"messages": ["保留我的聊天"]})
            modified = {**rows[0], "quote": "本地修改应保留"}
            with old.connect() as db:
                db.execute(
                    "UPDATE candidates SET data=? WHERE id=1", (json.dumps(modified),)
                )
            for _ in range(2):
                upgraded = Store(path)
                self.assertEqual(len(upgraded.candidates()), 1200)
                self.assertEqual(upgraded.candidates()[0], modified)
                self.assertEqual(
                    upgraded.get("private-session"), {"messages": ["保留我的聊天"]}
                )

    def test_copied_dataset_imports_identically_into_fresh_database(self):
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "candidates.json"
            copied.write_bytes(DATASET_PATH.read_bytes())
            rows = seed_candidates(copied)
            with patch(
                "backend.infrastructure.sqlite.seed_candidates", return_value=rows
            ):
                store = Store(Path(directory) / "fresh.db")
            self.assertEqual(store.candidates(), rows)

    def test_invalid_catalog_fails_before_database_is_created(self):
        data = json.loads(DATASET_PATH.read_text())
        for kind in ("duplicate", "underage", "bad_food"):
            broken = json.loads(json.dumps(data))
            if kind == "duplicate":
                broken["candidates"][1]["id"] = broken["candidates"][0]["id"]
            elif kind == "underage":
                broken["candidates"][0]["age"] = 17
            else:
                broken["candidates"][0]["food"] = "未支持的分类"
            with tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "invalid.json"
                source.write_text(json.dumps(broken))
                db_path = Path(directory) / "should-not-exist.db"
                with (
                    patch(
                        "backend.infrastructure.sqlite.seed_candidates",
                        side_effect=lambda source=source: seed_candidates(source),
                    ),
                    self.assertRaises(ValidationError),
                ):
                    Store(db_path)
                self.assertFalse(db_path.exists())
