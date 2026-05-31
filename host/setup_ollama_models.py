from __future__ import annotations

import argparse
import subprocess
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
        "path": MODEL_ROOT / "qwen2.5-7b-instruct-q4_k_m.gguf",
        "split_path": MODEL_ROOT / "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
        "system": "あなたは日本語TRPGのゲームマスターです。自然な日本語で簡潔に応答してください。",
        "template": (
            "{{ if .System }}<|im_start|>system\n{{ .System }}<|im_end|>\n{{ end }}"
            "{{ range .Messages }}<|im_start|>{{ .Role }}\n{{ .Content }}<|im_end|>\n{{ end }}"
            "<|im_start|>assistant\n"
        ),
        "parameters": [
            "PARAMETER stop <|im_start|>",
            "PARAMETER stop <|im_end|>",
        ],
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
    split_path = Path(spec["split_path"]) if spec.get("split_path") else None
    if not model_path.exists():
        if split_path and split_path.exists():
            print(
                f"[TRPG] Skip split GGUF for {name}: {split_path.name}\n"
                f"[TRPG] Merge the split files first, then place the merged file at:\n"
                f"[TRPG]   {model_path}\n"
                f"[TRPG] Example with llama.cpp:\n"
                f"[TRPG]   llama-gguf-split --merge \"{split_path}\" \"{model_path}\""
            )
            return
        print(f"[TRPG] Skip missing GGUF for {name}: {model_path}")
        return

    modelfile = MODEL_ROOT / f"Modelfile.{name}"
    lines = [f"FROM {model_path.as_posix()}"]
    if spec.get("template"):
        lines.append(f'TEMPLATE """{spec["template"]}"""')
    lines.append(f'SYSTEM """{spec["system"]}"""')
    lines.extend(spec.get("parameters") or [])
    lines.extend(["PARAMETER temperature 0.8", ""])
    modelfile.write_text("\n".join(lines), encoding="utf-8")
    try:
        print(f"[TRPG] Registering {name} from {model_path.name}")
        subprocess.run(["ollama", "create", name, "-f", str(modelfile)], check=True)
    finally:
        try:
            modelfile.unlink()
        except OSError:
            print(f"[TRPG] Warning: could not remove temporary Modelfile: {modelfile}")


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
