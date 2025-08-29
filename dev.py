#!/usr/bin/env python3
"""
dev.py - Corredor simple de comandos configurados en dev-commands.json
Tiene el proposito de estandarizar como corren los comandos en Windows y Linux,
permitiendo a vscode correrlos como tasks.

Uso:
  python dev.py --list
  python dev.py <command>
  python dev.py <command> --detach
"""

import argparse
import json
import os
import subprocess
import sys

DEFAULT_CONFIG = "dev-commands.json"


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
