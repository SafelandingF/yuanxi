"""验证层间依赖及可独立启动的应用工厂。"""

import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from backend.core.config import ModelConfig, Settings
from backend.domain.dating import available_meals, validate_choice
from backend.domain.schemas import DateChoice, DateRequest
from backend.main import create_app

BACKEND = Path(__file__).resolve().parents[1]


class LayerTests(unittest.TestCase):
    def test_inner_layers_do_not_depend_on_http_or_concrete_adapters(self):
        forbidden = {
            "domain": {
                "fastapi",
                "httpx",
                "sqlite3",
                "agents",
                "services",
                "api",
                "infrastructure",
                "core",
                "main",
                "bootstrap",
            },
            "agents": {
                "fastapi",
                "httpx",
                "sqlite3",
                "services",
                "api",
                "infrastructure",
                "core",
                "main",
                "bootstrap",
            },
            "services": {
                "fastapi",
                "httpx",
                "sqlite3",
                "api",
                "infrastructure",
                "core",
                "main",
                "bootstrap",
            },
        }
        for layer, blocked in forbidden.items():
            for path in (BACKEND / layer).glob("*.py"):
                for node in ast.walk(ast.parse(path.read_text())):
                    modules = []
                    if isinstance(node, ast.Import):
                        modules = [n.name for n in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        modules = [node.module or ""]
                    for module in modules:
                        self.assertFalse(
                            set(module.split(".")) & blocked,
                            f"{path.name} 不应依赖 {module}",
                        )

    def test_default_factory_does_not_read_config_or_open_database(self):
        with (
            patch("backend.main.load_settings") as config,
            patch("backend.bootstrap.Store") as database,
        ):
            app = create_app()
            self.assertFalse(hasattr(app.state, "services"))
            config.assert_not_called()
            database.assert_not_called()

    def test_budget_rule_runs_without_agents_or_web_service(self):
        request = DateRequest(
            session_id="test", candidate_id=1, budget=30, start="20:00"
        )
        limit, meals = available_meals({"budget": 100, "food": "都可以"}, request)
        too_expensive = DateChoice(
            meal_id="vegetarian",
            activity_id="book",
            drink_id="coffee",
            reason="测试",
            conflict_detected=False,
            conflict_description="",
        )
        with self.assertRaises(ValueError):
            validate_choice(too_expensive, meals, limit)


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_startup_builds_dependencies_and_shutdown_closes_model(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(
                database_path=Path(directory) / "test.db",
                llm=ModelConfig(api_key="test-only"),
            )
            with patch("backend.main.load_settings", return_value=settings):
                app = create_app()
                async with app.router.lifespan_context(app):
                    client = app.state.services.model.client
                    self.assertFalse(client.is_closed)
                    async with httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=app), base_url="http://test"
                    ) as http:
                        health = await http.get("/api/health")
                        self.assertEqual(health.json()["candidate_count"], 1200)
                self.assertTrue(client.is_closed)
