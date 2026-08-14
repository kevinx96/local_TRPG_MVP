import json
import unittest
import uuid
from pathlib import Path

from fastapi import HTTPException

from host import app as app_module


class ScenarioEditorApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp_root = Path.cwd() / ".tmp-test"
        self.tmp_root.mkdir(exist_ok=True)
        self.tmp_path = self.tmp_root / f"editor-{uuid.uuid4().hex}"
        self.tmp_path.mkdir()
        self.original_dir = app_module.PROCESSED_SCENARIO_DIR
        app_module.PROCESSED_SCENARIO_DIR = self.tmp_path

    def tearDown(self):
        app_module.PROCESSED_SCENARIO_DIR = self.original_dir

    def pack(self, title="Test Scenario"):
        return {
            "meta": {
                "title": title,
                "summary": "Small editable scenario.",
                "language": "ja",
                "initial_scene": "start",
            },
            "rules": ["Do not act for the player."],
            "scenes": [
                {
                    "id": "start",
                    "title": "Start",
                    "description": "Opening scene.",
                    "keywords": ["start"],
                    "fallback_choices": [{"text": "Look around", "preview": "", "risk": ""}],
                }
            ],
            "locations": [],
            "npcs": [],
            "items": [],
            "clues": [],
            "fallback_choices": [{"text": "Wait", "preview": "", "risk": ""}],
        }

    def test_list_get_and_save_scenario(self):
        scenario_path = self.tmp_path / "demo.json"
        scenario_path.write_text(json.dumps(self.pack(), ensure_ascii=False), encoding="utf-8")
        (self.tmp_path / "demo-restore.json").write_text(
            json.dumps(self.pack("Backup"), ensure_ascii=False),
            encoding="utf-8",
        )
        (self.tmp_path / "scenario_pack.schema.json").write_text("{}", encoding="utf-8")

        listed = app_module.api_list_scenarios()
        self.assertEqual([item["filename"] for item in listed["scenarios"]], ["demo.json"])

        loaded = app_module.api_get_scenario("demo.json")
        scenario = loaded["scenario"]
        scenario["scenes"][0]["fallback_choices"].append({"text": "Open the door", "preview": "", "risk": "DC10"})

        saved = app_module.api_save_scenario("demo.json", app_module.ScenarioSaveRequest(scenario=scenario))
        self.assertEqual(saved["filename"], "demo.json")
        written = json.loads(scenario_path.read_text(encoding="utf-8"))
        self.assertEqual(written["scenes"][0]["fallback_choices"][1]["text"], "Open the door")

    def test_create_scenario_and_reject_path_traversal(self):
        created = app_module.api_create_scenario(app_module.ScenarioCreateRequest(filename="new_pack.json", scenario=self.pack("New")))
        self.assertEqual(created["filename"], "new_pack.json")
        self.assertTrue((self.tmp_path / "new_pack.json").exists())

        with self.assertRaises(HTTPException) as caught:
            app_module.api_get_scenario("../config.json")
        self.assertEqual(caught.exception.status_code, 400)

    def test_reject_invalid_pack(self):
        with self.assertRaises(HTTPException) as caught:
            app_module.api_create_scenario(app_module.ScenarioCreateRequest(filename="bad.json", scenario={"meta": {}}))
        self.assertEqual(caught.exception.status_code, 400)

    def test_config_info_does_not_expose_backend_secrets(self):
        original_load_config = app_module.load_config
        app_module.load_config = lambda: {
            "active_backend": "ollama",
            "backends": {
                "ollama": {
                    "base_url": "https://ollama.example.com/v1",
                    "model": "qwen",
                    "fallback_models": ["elyza"],
                    "api_key": "secret-key",
                    "headers": {
                        "CF-Access-Client-Id": "client-id",
                        "CF-Access-Client-Secret": "client-secret",
                    },
                }
            },
        }
        try:
            config = app_module.config_info()
        finally:
            app_module.load_config = original_load_config

        backend = config["backends"]["ollama"]
        self.assertEqual(backend["model"], "qwen")
        self.assertNotIn("api_key", backend)
        self.assertNotIn("headers", backend)

    def test_html_entrypoints_are_not_cached(self):
        for response in (app_module.index(), app_module.editor()):
            self.assertEqual(response.headers.get("Cache-Control"), "no-store, max-age=0")
            self.assertEqual(response.headers.get("Pragma"), "no-cache")


if __name__ == "__main__":
    unittest.main()
