"""Unit tests for the ModelScope client.

    python tests/test_client.py

The network-dependent test is skipped automatically when the endpoint is not
reachable, so the suite still passes offline.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modelscope_client import (  # noqa: E402
    CURATED_MODELS,
    DEFAULT_MODEL,
    ModelScopeClient,
    ModelScopeError,
    pick_model,
)


class ErrorExplanationTests(unittest.TestCase):
    def test_401_points_at_token_page(self) -> None:
        message = ModelScopeClient._explain(401, "{}")
        self.assertIn("访问令牌", message)

    def test_429_mentions_quota(self) -> None:
        self.assertIn("额度", ModelScopeClient._explain(429, "{}"))

    def test_404_mentions_model(self) -> None:
        self.assertIn("模型", ModelScopeClient._explain(404, "{}"))

    def test_5xx_mentions_service(self) -> None:
        self.assertIn("服务", ModelScopeClient._explain(503, "{}"))


class PickModelTests(unittest.TestCase):
    def test_preferred_model_wins(self) -> None:
        self.assertEqual(pick_model(["Qwen/Qwen3.5-27B", "x/y"], "Qwen/Qwen3.5-27B"), "Qwen/Qwen3.5-27B")

    def test_falls_back_to_curated(self) -> None:
        available = ["some/other", CURATED_MODELS[1]]
        self.assertEqual(pick_model(available, DEFAULT_MODEL), CURATED_MODELS[1])

    def test_falls_back_to_first(self) -> None:
        self.assertEqual(pick_model(["a/b", "c/d"], DEFAULT_MODEL), "a/b")

    def test_empty_list_keeps_default(self) -> None:
        self.assertEqual(pick_model([], DEFAULT_MODEL), DEFAULT_MODEL)


class LiveEndpointTests(unittest.TestCase):
    def test_list_models_reachable(self) -> None:
        client = ModelScopeClient("")
        try:
            models = client.list_models()
        except ModelScopeError as error:
            self.skipTest(f"ModelScope endpoint unreachable: {error}")
        self.assertTrue(models)
        self.assertTrue(any(model.startswith("Qwen/") for model in models))


if __name__ == "__main__":
    unittest.main()
