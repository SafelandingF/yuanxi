"""验证层间依赖及可独立启动的应用工厂。"""

import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from backend.core.config import ModelConfig, Settings
from backend.domain.dating import (
    available_meals,
    recommended_combinations,
    validate_choice,
)
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

    def test_local_planner_uses_budget_interests_and_avoids_last_plan(self):
        profile = {
            "interests": ["电影", "咖啡"],
            "rhythm": "规律慢生活",
        }
        candidate = {
            "budget": 120,
            "food": "清淡、不太辣",
            "interests": ["电影", "散步"],
            "rhythm": "规律慢生活",
        }
        request = DateRequest(
            session_id="test",
            candidate_id=1,
            budget=120,
            start="18:00",
            spending_style="均衡安排",
        )
        limit, meals = available_meals(candidate, request)
        target, choices = recommended_combinations(
            profile, candidate, request, meals, limit
        )
        self.assertEqual(target, 90)
        self.assertTrue(choices)
        self.assertTrue(all(choice["total"] <= limit for choice in choices))
        self.assertLessEqual(
            max(
                sum(choice["meal_id"] == meal["id"] for choice in choices)
                for meal in meals
            ),
            2,
        )

        first = choices[0]
        retry = request.model_copy(
            update={
                "avoid_ids": [
                    first["meal_id"],
                    first["activity_id"],
                    first["drink_id"],
                ]
            }
        )
        _, alternatives = recommended_combinations(
            profile, candidate, retry, meals, limit
        )
        self.assertNotEqual(alternatives[0], first)

    def test_meal_preference_and_dietary_rules_are_applied_locally(self):
        candidate = {"budget": 150, "food": "都可以、爱尝鲜"}
        request = DateRequest(
            session_id="test",
            candidate_id=1,
            budget=150,
            start="18:00",
            meal_preference="想吃锅类",
            food_restrictions=["不吃辣"],
        )
        _, meals = available_meals(candidate, request)
        self.assertTrue(meals)
        self.assertTrue(all("锅类" in meal["categories"] for meal in meals))
        self.assertTrue(all(not meal["spicy"] for meal in meals))


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_unconfigured_startup_exposes_only_setup_routes(self):
        with (
            patch("backend.main.load_settings", side_effect=RuntimeError("missing")),
            patch(
                "backend.api.routes.config_status",
                return_value={
                    "configured": False,
                    "provider": "openai-compatible",
                    "base_url": "",
                    "model": "",
                    "has_api_key": False,
                },
            ),
        ):
            app = create_app()
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test"
                ) as http:
                    health = await http.get("/api/health")
                    self.assertEqual(health.json()["status"], "setup_required")
                    config = await http.get("/api/config")
                    self.assertFalse(config.json()["configured"])
                    blocked = await http.get("/api/agent/sessions/unknown")
                    self.assertEqual(blocked.status_code, 503)

    async def test_config_submission_initializes_services_without_returning_key(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(
                database_path=Path(directory) / "test.db",
                llm=ModelConfig(
                    api_key="new-local-secret",
                    provider="openai-compatible",
                    base_url="https://models.example/v1",
                    model="example-model",
                ),
            )
            with (
                patch("backend.main.load_settings", side_effect=RuntimeError("missing")),
                patch(
                    "backend.api.routes.settings_from_update",
                    return_value=settings,
                ),
                patch("backend.api.routes.save_settings") as save,
            ):
                app = create_app()
                async with app.router.lifespan_context(app):
                    async with httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=app), base_url="http://test"
                    ) as http:
                        response = await http.put(
                            "/api/config",
                            json={
                                "api_key": "new-local-secret",
                                "provider": "openai-compatible",
                                "base_url": "https://models.example/v1",
                                "model": "example-model",
                            },
                        )
                        self.assertEqual(response.status_code, 200)
                        self.assertTrue(response.json()["configured"])
                        self.assertNotIn("new-local-secret", response.text)
                        health = await http.get("/api/health")
                        self.assertEqual(health.json()["candidate_count"], 1200)
                        save.assert_called_once_with(settings)

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
