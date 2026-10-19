"""Build a Windows executable with PyInstaller (run locally; the API key is never bundled).

Usage:
    python -m scripts.build_exe                     # folder build: dist/LocalTRPG/LocalTRPG.exe + zip
    python -m scripts.build_exe --onefile           # single dist/LocalTRPG.exe
    python -m scripts.build_exe --with-local-config # also copy host/local_config.json next to the exe (personal use only)
    python -m scripts.build_exe --demo-endpoint https://<worker>.workers.dev   # shareable demo via the key proxy
                                                    # (token from --demo-token or DEMO_TOKEN; see workers/gemini-proxy)

After building, the bundle is audited: every compressed module is unpacked and searched for the
configured API key, and credential-holding modules must be absent. Any hit deletes the output.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "LocalTRPG"
DATA = [
    ("client", "client"),
    ("host/config.json", "host"),
    ("host/prompt/processed/dragon_rpg.json", "host/prompt/processed"),
    ("host/prompt/processed/dragon_rpg_hybrid.json", "host/prompt/processed"),
    ("host/prompt/processed/scenario_pack.schema.json", "host/prompt/processed"),
]
# host.auto_tagger and the key files hold credentials; the rest are only used by offline scenario tools.
EXCLUDE = ["host.auto_tagger", "host.setup_ollama_models", "host.generate_hybrid_scenario", "host.expand_dragon_scenario",
           "google.generativeai", "google.ai", "googleapiclient", "grpc", "torch", "triton", "tensorflow",
           "transformers", "numpy", "pandas", "scipy", "matplotlib", "IPython", "jupyter", "notebook",
           "docx", "pypdf", "win32com", "PIL", "tkinter"]
FORBIDDEN_MODULES = ("host.auto_tagger",)
FORBIDDEN_FILES = ("local_config.json", "auto_tagger", "gemini_api_key")


def build(onefile: bool) -> Path:
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--name", NAME,
               "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build"),
               "--collect-submodules", "uvicorn", "--onefile" if onefile else "--onedir"]
    for module in EXCLUDE:
        command += ["--exclude-module", module]
    for source, target in DATA:
        command += ["--add-data", f"{ROOT / source}{os.pathsep}{target}"]
    command.append(str(ROOT / "packaging" / "launcher.py"))
    subprocess.run(command, check=True, cwd=ROOT)
    return ROOT / "dist" / (f"{NAME}.exe" if onefile else NAME)


def _secrets() -> list[bytes]:
    values = [os.environ.get("GEMINI_API_KEY", "")]
    values += [key.strip() for key in os.environ.get("GEMINI_API_KEYS", "").split(",")]
    local = ROOT / "host" / "local_config.json"
    if local.exists():
        config = json.loads(local.read_text(encoding="utf-8-sig"))
        values += [str(backend.get("api_key") or "") for backend in (config.get("backends") or {}).values()]
        values += [key for backend in (config.get("backends") or {}).values()
                   for key in backend.get("api_keys", []) if isinstance(key, str)]
        values += [str(value) for backend in (config.get("backends") or {}).values()
                   for value in (backend.get("headers") or {}).values() if len(str(value)) >= 16]
    return [value.strip().encode() for value in values if value.strip() and value not in ("ollama", "koboldcpp")]


def _archive_payloads(exe: Path):
    """Yield (name, bytes) for every entry inside the executable's archives, decompressing modules."""
    from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader
    carchive = CArchiveReader(str(exe))
    for name in carchive.toc:
        data = carchive.extract(name)
        yield name, data
        if name.endswith(".pyz") or name == "PYZ.pyz" or data[:4] == b"PYZ\0":
            path = ROOT / "build" / "_audit.pyz"
            path.write_bytes(data)
            pyz = ZlibArchiveReader(str(path))
            for module in pyz.toc:
                yield f"pyz:{module}", pyz.extract(module, raw=True) or b""


def audit(output: Path) -> None:
    bundle = output if output.is_dir() else output.parent
    exe = bundle / f"{NAME}.exe"
    secrets = _secrets()
    problems = [str(p) for p in bundle.rglob("*") if p.is_file() and p.parent != bundle
                and any(name in p.name for name in FORBIDDEN_FILES)]
    for path in bundle.rglob("*"):
        if path.is_file() and path.name not in FORBIDDEN_FILES:
            data = path.read_bytes()
            problems += [f"{path}: raw key" for secret in secrets if secret in data]
    modules = 0
    for name, data in _archive_payloads(exe):
        modules += name.startswith("pyz:")
        if any(name == f"pyz:{forbidden}" for forbidden in FORBIDDEN_MODULES):
            problems.append(f"{name}: forbidden module")
        for candidate in (data, _try_inflate(data)):
            problems += [f"{name}: key inside archive" for secret in secrets if candidate and secret in candidate]
    if problems:
        shutil.rmtree(ROOT / "dist", ignore_errors=True)
        raise SystemExit("credential audit failed, output deleted:\n" + "\n".join(sorted(set(problems))))
    print(f"[audit] ok: {modules} bundled modules checked, {len(secrets)} secret(s) searched, none found")


def _try_inflate(data: bytes) -> bytes:
    try:
        return zlib.decompress(data)
    except zlib.error:
        return b""


def write_demo_config(folder: Path, endpoint: str, token: str) -> None:
    """Point the bundle at the key proxy; the optional demo token is shareable, the Gemini keys never are."""
    if token and token.encode() in _secrets():
        raise SystemExit("the demo token matches a configured API key; use the proxy's own token")
    base_url = endpoint.rstrip("/")
    if not base_url.endswith("/v1beta"):
        base_url += "/v1beta"
    gemini = {"base_url": base_url, "api_key": token} if token else {"base_url": base_url}
    config = {"active_backend": "gemini", "backends": {"gemini": gemini}}
    (folder / "local_config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    shutil.copy2(ROOT / "packaging" / "README_DEMO.txt", folder / "README_RUN.txt")
    print(f"[build] demo config points at {base_url}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--onefile", action="store_true")
    parser.add_argument("--with-local-config", action="store_true")
    parser.add_argument("--demo-endpoint", help="key proxy URL; writes a shareable local_config.json next to the exe")
    parser.add_argument("--demo-token", default=os.environ.get("DEMO_TOKEN", ""))
    args = parser.parse_args()
    if args.demo_endpoint and args.with_local_config:
        parser.error("--demo-endpoint and --with-local-config are mutually exclusive")
    output = build(args.onefile)
    folder = output if output.is_dir() else output.parent
    audit(output)
    for name in ("README_RUN.txt", "local_config.example.json"):
        shutil.copy2(ROOT / "packaging" / name, folder / name)
    if args.demo_endpoint:
        write_demo_config(folder, args.demo_endpoint, args.demo_token)
    # The shareable zip is made before any personal config is copied; a demo config holds only the proxy token.
    if output.is_dir():
        archive = shutil.make_archive(str(ROOT / "dist" / NAME), "zip", root_dir=output.parent, base_dir=output.name)
        print(f"[build] {output / (NAME + '.exe')}\n[build] {archive}")
    else:
        print(f"[build] {output}")
    if args.with_local_config:
        source = ROOT / "host" / "local_config.json"
        if source.exists():
            shutil.copy2(source, folder / "local_config.json")
            print("[build] copied local_config.json next to the exe for personal use — do not share this folder.")


if __name__ == "__main__":
    main()
