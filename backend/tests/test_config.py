"""Provider-neutral configuration, with legacy Ark compatibility."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from backend.core.config import ModelConfig, load_settings
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


class PayloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_generic_payload_omits_ark_extension(self):
        for provider in ["openai-compatible", "volcengine-ark"]:
            adapter = Ark(ModelConfig(provider=provider, api_key="test-only-key"))
            try:
                payload = adapter.payload("system", {"text": "hello"})
                self.assertEqual("thinking" in payload, provider == "volcengine-ark")
            finally:
                await adapter.aclose()
