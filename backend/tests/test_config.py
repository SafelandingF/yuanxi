"""Provider-neutral configuration, with legacy Ark compatibility."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from backend.core.config import (
    ConfigUpdate,
    ModelConfig,
    config_status,
    load_port,
    load_settings,
    save_settings,
    settings_from_update,
)
from backend.infrastructure.ark import Ark


class ConfigTests(unittest.TestCase):
    def load(self, llm):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.yaml").write_text(
                yaml.safe_dump({"apikey": "test-only-key", "llm": llm})
            )
            with patch("backend.core.config.ROOT", root):
                return load_settings()

    def test_custom_provider(self):
        config = self.load(
            {
                "provider": "openai-compatible",
                "base_url": "https://models.example/v1",
                "model": "custom-model",
            }
        )
        self.assertEqual(config.llm.base_url, "https://models.example/v1")
        self.assertEqual(config.llm.model, "custom-model")

    def test_legacy_key_only(self):
        config = self.load({})
        self.assertEqual(config.llm.provider, "volcengine-ark")
        self.assertEqual(config.llm.model, "doubao-seed-2-0-pro-260215")

    def test_invalid_urls_and_missing_fields(self):
        for url in [
            "file:///tmp/a",
            "https://user:secret@models.example/v1",
            "https://models.example/v1?key=secret",
            "https://models.example/v1/chat/completions",
        ]:
            with self.assertRaises(RuntimeError):
                self.load(
                    {
                        "provider": "openai-compatible",
                        "base_url": url,
                        "model": "example",
                    }
                )
        with self.assertRaises(RuntimeError):
            self.load({"provider": "openai-compatible"})

    def test_first_run_status_and_safe_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.yaml").write_text(
                yaml.safe_dump(
                    {
                        "apikey": "",
                        "app": {"port": 8123, "database_path": "./data/test.db"},
                        "llm": {
                            "provider": "openai-compatible",
                            "base_url": "",
                            "model": "",
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch("backend.core.config.ROOT", root):
                status = config_status()
                self.assertFalse(status["configured"])
                self.assertFalse(status["has_api_key"])
                self.assertNotIn("api_key", status)
                self.assertEqual(load_port(), 8123)

                settings = settings_from_update(
                    ConfigUpdate(
                        api_key="local-secret",
                        provider="openai-compatible",
                        base_url="https://models.example/v1",
                        model="example-model",
                    )
                )
                save_settings(settings)

                saved_status = config_status()
                self.assertTrue(saved_status["configured"])
                self.assertNotIn("local-secret", str(saved_status))
                saved = yaml.safe_load((root / "config.yaml").read_text("utf-8"))
                self.assertEqual(saved["apikey"], "local-secret")
                self.assertEqual(saved["app"]["port"], 8123)

                retained = settings_from_update(
                    ConfigUpdate(
                        api_key="",
                        provider="openai-compatible",
                        base_url="https://models.example/v2",
                        model="replacement-model",
                    )
                )
                self.assertEqual(
                    retained.llm.api_key.get_secret_value(), "local-secret"
                )


class PayloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_generic_payload_omits_ark_extension(self):
        for provider in ["openai-compatible", "volcengine-ark"]:
            adapter = Ark(ModelConfig(provider=provider, api_key="test-only-key"))
            try:
                payload = adapter.payload("system", {"text": "hello"})
                self.assertEqual("thinking" in payload, provider == "volcengine-ark")
            finally:
                await adapter.aclose()
