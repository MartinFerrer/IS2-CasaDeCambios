#!/usr/bin/env python3
"""dev.py - Corredor simple de comandos configurados en dev-commands.json
Platform-aware replacement for {TAILWIND_BIN} so tailwind-watch-local works.
Usage:
  python dev.py --list
  python dev.py <command>
  python dev.py <command> --detach
"""

import argparse
import json
import os
import platform
import subprocess
import sys

DEFAULT_CONFIG = "dev-commands.json"


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def download_file(url, dest):
    import requests

    """Download a file from URL to destination"""
    print(f"Downloading {url} to {dest}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(dest, "wb") as f:
        f.writelines(response.iter_content(chunk_size=8192))
    os.chmod(dest, 0o755)  # Make executable


def find_tailwind_bin():
    """Return the absolute path to the correct tailwind binary inside the repo.
    Downloads from GitHub if not present.
    """
    root = os.path.abspath(os.getcwd())
    version = "v4.1.12"

    if platform.system() == "Windows":
        bin_name = "tailwindcss-windows-x64.exe"
        platform_name = "windows-x64.exe"
    elif platform.system() == "Darwin":
        bin_name = "tailwindcss-macos-x64"
        platform_name = "macos-x64"
    else:
        bin_name = "tailwindcss-linux-x64"
        platform_name = "linux-x64"

    bin_path = os.path.join(root, "app", "static", "css", bin_name)

    if not os.path.exists(bin_path):
        os.makedirs(os.path.dirname(bin_path), exist_ok=True)
        base_url = f"https://github.com/tailwindlabs/tailwindcss/releases/download/{version}"
        download_file(f"{base_url}/tailwindcss-{platform_name}", bin_path)

    return bin_path


def download_tailwind_linux():
    """Download the Linux-x64 tailwind binary into app/static/css/tailwindcss-linux-x64
    on the host filesystem (useful for making the file available to docker compose).
    """
    root = os.path.abspath(os.getcwd())
    version = "v4.1.12"
    bin_name = "tailwindcss-linux-x64"
    bin_path = os.path.join(root, "app", "static", "css", bin_name)

    if os.path.exists(bin_path):
        print(f"{bin_path} already exists — skipping download.")
        return bin_path

    os.makedirs(os.path.dirname(bin_path), exist_ok=True)
    base_url = f"https://github.com/tailwindlabs/tailwindcss/releases/download/{version}"
    download_file(f"{base_url}/{bin_name}", bin_path)
    return bin_path


def replace_placeholders(cmd_list):
    """Replace {TAILWIND_BIN} placeholder with platform-specific absolute path."""
    tailwind_path = find_tailwind_bin()
    out = []
    for part in cmd_list:
        if isinstance(part, str) and "{TAILWIND_BIN}" in part:
            out.append(part.replace("{TAILWIND_BIN}", tailwind_path))
        else:
            out.append(part)
    return out


def run_attached(cmd, cwd, env):
    print(f"Running (attached): {' '.join(cmd)}  (cwd={cwd})")
    rc = subprocess.call(cmd, cwd=cwd, env=env)
    if rc != 0:
        raise SystemExit(rc)


def run_detached(cmd, cwd, env):
    print(f"Running (detached): {' '.join(cmd)}  (cwd={cwd})")
    p = subprocess.Popen(cmd, cwd=cwd, env=env)
    print(f"PID: {p.pid}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", help="command name from dev-commands.json")
    parser.add_argument("--list", action="store_true", help="list commands")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="path to config file")
    parser.add_argument("--detach", action="store_true", help="start detached")
    args = parser.parse_args()

    # Handle direct helper commands that do not require dev-commands.json
    if args.name == "install-tailwind":
        download_tailwind_linux()
        return

    cfg = load_config(args.config)
    commands = cfg.get("commands", {})

    if args.list or not args.name:
        print("Available commands:")
        for k, v in sorted(commands.items()):
            print(f"  {k} -> {' '.join(v.get('cmd', []))}  (cwd={v.get('cwd', '.')})")
        if not args.name:
            return

    if args.name not in commands:
        print(f"Unknown command: {args.name}")
        sys.exit(2)

    entry = commands[args.name]
    cmd = entry.get("cmd")
    cwd = os.path.abspath(entry.get("cwd", "."))
    env = os.environ.copy()
    env.update(entry.get("env", {}))

    if not isinstance(cmd, list):
        print("Command must be an array in dev-commands.json")
        sys.exit(3)

    # Replace placeholders
    cmd = replace_placeholders(cmd)

    try:
        if args.detach:
            run_detached(cmd, cwd, env)
        else:
            run_attached(cmd, cwd, env)
    except KeyboardInterrupt:
        print("Interrupted.")
        sys.exit(130)


if __name__ == "__main__":
    main()
