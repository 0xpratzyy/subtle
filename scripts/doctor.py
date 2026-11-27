#!/usr/bin/env python3
"""Check Subtle dependencies from Windows, macOS, or Linux."""
import argparse
import importlib.util
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def version(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        return (result.stdout or result.stderr).strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return "available"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-timings", action="store_true", help="check a render using supplied word timings")
    args = parser.parse_args()
    missing = False
    print("Subtle doctor")

    def check(name, okay, detail, install=""):
        nonlocal missing
        if okay:
            print(f"  ok       {name:<13} {detail}")
        else:
            missing = True
            print(f"  MISSING  {name:<13} {install}")

    ffmpeg = shutil.which("ffmpeg") and shutil.which("ffprobe")
    check("ffmpeg", bool(ffmpeg), version(["ffmpeg", "-version"]),
          "install ffmpeg (Windows: winget install ffmpeg; macOS: brew install ffmpeg)")
    check("python", sys.version_info >= (3, 9), sys.version.split()[0], "install Python 3.9 or newer")
    node = shutil.which("node")
    node_ok = False
    node_version = "not found"
    if node:
        node_version = version([node, "--version"])
        try:
            node_ok = int(node_version.lstrip("v").split(".")[0]) >= 18
        except ValueError:
            pass
    check("node", node_ok, node_version, "install Node 18+ (Windows: winget install OpenJS.NodeJS.LTS)")

    uv = shutil.which("uv")
    python_deps = importlib.util.find_spec("numpy") and importlib.util.find_spec("PIL")
    check("numpy+pillow", bool(uv or python_deps), version([uv, "--version"]) if uv else "importable from Python",
          "install uv (Windows: winget install astral-sh.uv) or install numpy and pillow")
    if args.from_timings:
        print("  optional whisper       skipped for supplied word timings")
    elif importlib.util.find_spec("faster_whisper") or uv:
        print("  ok       whisper       faster-whisper available through Python/uv (first run downloads the model)")
    elif sys.platform == "darwin" and platform.machine() == "arm64" and importlib.util.find_spec("mlx_whisper"):
        print("  ok       whisper       mlx-whisper importable")
    else:
        missing = True
        print("  MISSING  whisper       install uv or: pip install faster-whisper")

    if sys.platform == "darwin":
        swift = shutil.which("swiftc")
        print(f"  optional behind-mode  {'Swift available; builds on first use' if swift else 'install Xcode command line tools for Apple Vision styles'}")
    else:
        print("  optional behind-mode  needs macOS / Apple Vision; other styles work here")
    if (ROOT / "template" / "node_modules" / "remotion").exists():
        print("  ok       remotion     installed in template/node_modules")
    else:
        print("  optional remotion     first render installs packages with npm ci")
    print("Ready." if not missing else "Fix the MISSING lines above, then run this again.")
    return int(missing)


if __name__ == "__main__":
    raise SystemExit(main())
