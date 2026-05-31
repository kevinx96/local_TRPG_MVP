from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path


HOST_ROOT = Path(__file__).resolve().parent
MODEL_ROOT = HOST_ROOT / "models"

MODEL_SPECS = [
    {
        "name": "elyza-jp-8b-local",
        "path": MODEL_ROOT / "Llama-3-ELYZA-JP-8B-q4_k_m.gguf",
        "system": "あなたは日本語TRPGのゲームマスターです。自然な日本語で簡潔に応答してください。",
    },
    {
        "name": "qwen2.5-7b-instruct-local",
        "path": MODEL_ROOT / "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
        "system": "あなたは日本語TRPGのゲームマスターです。自然な日本語で簡潔に応答してください。",
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Register local GGUF files with Ollama.")
    parser.add_argument("--only", choices=[spec["name"] for spec in MODEL_SPECS])
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    installed = set(list_ollama_models())
    targets = [spec for spec in MODEL_SPECS if args.only in (None, spec["name"])]
    for spec in targets:
        if args.skip_existing and spec["name"] in installed:
            print(f"[TRPG] Already installed: {spec['name']}")
            continue
        register_model(spec)

    print("[TRPG] Ollama models after setup:")
    for name in list_ollama_models():
        print(f"  - {name}")
    return 0


def register_model(spec: dict[str, object]) -> None:
    name = str(spec["name"])
    model_path = Path(spec["path"])
    if not model_path.exists():
        print(f"[TRPG] Skip missing GGUF for {name}: {model_path}")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        modelfile = Path(temp_dir) / "Modelfile"
        modelfile.write_text(
            "\n".join(
                [
                    f"FROM {model_path.as_posix()}",
                    f'SYSTEM """{spec["system"]}"""',
                    "PARAMETER temperature 0.8",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print(f"[TRPG] Registering {name} from {model_path.name}")
        subprocess.run(["ollama", "create", name, "-f", str(modelfile)], check=True)


def list_ollama_models() -> list[str]:
    result = subprocess.run(["ollama", "list"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    names: list[str] = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if parts:
            names.append(parts[0])
    return names


if __name__ == "__main__":
    raise SystemExit(main())
