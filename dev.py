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


def get_enhanced_env():
    """Get environment with enhanced PATH for finding system tools like Heroku CLI"""
    env = os.environ.copy()

    # On Windows, add common installation paths for Heroku CLI
    if platform.system() == "Windows":
        additional_paths = [
            "C:\\Program Files\\heroku\\bin",
            "C:\\Program Files (x86)\\heroku\\bin",
            "C:\\ProgramData\\chocolatey\\bin",
            os.path.expanduser("~\\AppData\\Local\\heroku\\bin"),
            os.path.expanduser("~\\AppData\\Roaming\\npm"),
        ]
        current_path = env.get("PATH", "")
        for path in additional_paths:
            if os.path.exists(path) and path not in current_path:
                env["PATH"] = path + os.pathsep + current_path

        # Validate Heroku CLI presence and set full path if found
        heroku_cmd = "heroku.cmd" if platform.system() == "Windows" else "heroku"
        for path in env["PATH"].split(os.pathsep):
            full_path = os.path.join(path, heroku_cmd)
            if os.path.exists(full_path):
                env["HEROKU_CLI_PATH"] = full_path
                break
        else:
            print(
                "WARNING: Heroku CLI not found in PATH. Ensure it is installed and accessible."
            )

    return env


def get_heroku_command():
    """Get the Heroku command, using the full path if available."""
    env = get_enhanced_env()
    return env.get("HEROKU_CLI_PATH", "heroku")


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
        base_url = (
            f"https://github.com/tailwindlabs/tailwindcss/releases/download/{version}"
        )
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
    base_url = (
        f"https://github.com/tailwindlabs/tailwindcss/releases/download/{version}"
    )
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


def load_env_file(path):
    """Load environment variables from a .env style file"""
    env_vars = {}
    if not os.path.exists(path):
        return env_vars

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    return env_vars


def deploy_to_heroku():
    """Explicit deployment to Heroku using Docker commands"""
    print("=== Deploying to Heroku ===")

    # Load environment variables from .env.heroku
    heroku_env = load_env_file(".env.heroku")

    app_name = heroku_env.get("HEROKU_APP_NAME")
    if not app_name:
        print("ERROR: Missing HEROKU_APP_NAME in .env.heroku file")
        sys.exit(1)

    print(f"App name: {app_name}")

    # Get the full path to Heroku CLI
    heroku_command = get_heroku_command()

    try:
        # Step 1: Log in to Heroku Container Registry
        print("\n1. Logging in to Heroku Container Registry...")
        subprocess.run([heroku_command, "container:login"], check=True)

        # Step 2: Set the app stack to container
        print("\n2. Setting Heroku app stack to 'container'...")
        subprocess.run(
            [heroku_command, "stack:set", "container", "--app", app_name], check=True
        )

        # Step 3: Build the Docker image
        print("\n3. Building the Docker image...")
        subprocess.run(
            [
                "docker",
                "buildx",
                "build",
                "--provenance=false",
                "--platform=linux/amd64",
                "-t",
                f"registry.heroku.com/{app_name}/web",
                "./app",
            ],
            check=True,
        )

        # Step 4: Push the Docker image
        print("\n4. Pushing the Docker image...")
        subprocess.run(
            ["docker", "push", f"registry.heroku.com/{app_name}/web"], check=True
        )

        # Step 5: Release the image
        print("\n5. Releasing the Docker image...")
        subprocess.run(
            [heroku_command, "container:release", "web", "--app", app_name], check=True
        )

        print(f"\n🎉 Successfully deployed to Heroku app: {app_name}")
        
        # Step 6: Deploy simulador-api (if exists)
        simulador_app_name = "global-exchange-simulador"
        if os.path.exists("api_externo_simulador"):
            print(f"\n=== Deploying Simulador API to {simulador_app_name} ===")
            try:
                # Deploy using Docker (same as main app)
                print("\n6. Logging in to Heroku Container Registry...")
                subprocess.run([heroku_command, "container:login"], check=True)

                print("\n7. Setting simulador app stack to 'container'...")
                subprocess.run(
                    [heroku_command, "stack:set", "container", "--app", simulador_app_name], check=True
                )

                print("\n8. Building the simulador Docker image...")
                subprocess.run(
                    [
                        "docker",
                        "buildx",
                        "build",
                        "--provenance=false",
                        "--platform=linux/amd64",
                        "-t",
                        f"registry.heroku.com/{simulador_app_name}/web",
                        "./api_externo_simulador",
                    ],
                    check=True,
                )

                print("\n9. Pushing the simulador Docker image...")
                subprocess.run(
                    ["docker", "push", f"registry.heroku.com/{simulador_app_name}/web"], check=True
                )

                print("\n10. Releasing the simulador Docker image...")
                subprocess.run(
                    [heroku_command, "container:release", "web", "--app", simulador_app_name], check=True
                )

                print(f"\n🎉 Successfully deployed simulador-api to: {simulador_app_name}")
            except subprocess.CalledProcessError as e:
                print(f"\nWARNING: Simulador deployment failed with return code {e.returncode}")
                print("Main app deployed successfully, but simulador deployment failed.")
        else:
            print("\nSkipping simulador-api deployment (folder not found)")
            
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Deployment step failed with return code {e.returncode}")
        sys.exit(1)


def deploy_with_docker_manual(app_name, api_key):
    """Fallback manual Docker deployment approach"""
    print("Attempting manual Docker deployment...")

    try:
        # Login to Heroku Container Registry manually
        print("\n1. Manual Docker login to Heroku Container Registry...")
        login_cmd = [
            "docker",
            "login",
            "--username=_",
            "--password-stdin",
            "registry.heroku.com",
        ]
        login_proc = subprocess.Popen(login_cmd, stdin=subprocess.PIPE, text=True)
        login_proc.communicate(input=api_key)
        if login_proc.returncode != 0:
            print("ERROR: Docker login failed")
            sys.exit(1)

        # Build with explicit platform and architecture
        print("\n2. Building Docker image with explicit platform targeting...")

        # Try method 1: Use buildx with explicit platform
        build_cmd = [
            "docker",
            "buildx",
            "build",
            "--provenance=false",
            "--platform=linux/amd64",
            "--load",
            "-t",
            f"registry.heroku.com/{app_name}/web",
            "./app",
        ]

        build_result = subprocess.run(build_cmd, capture_output=True, text=True)
        if build_result.returncode != 0:
            print("   Buildx failed, trying alternative build method...")
            print("   Build stderr:", build_result.stderr)

            # Try method 2: Force use of default builder
            print("   Switching to default Docker builder...")
            subprocess.run(["docker", "buildx", "use", "default"], capture_output=True)

            build_cmd_alt = [
                "docker",
                "build",
                "--platform=linux/amd64",
                "-t",
                f"registry.heroku.com/{app_name}/web",
                "./app",
            ]

            if subprocess.call(build_cmd_alt) != 0:
                print("ERROR: All build methods failed")
                sys.exit(1)

        print("   ✅ Build completed successfully")

        # Verify image architecture
        print("\n3. Verifying image architecture...")
        inspect_cmd = [
            "docker",
            "inspect",
            f"registry.heroku.com/{app_name}/web",
            "--format",
            "{{.Architecture}}",
        ]
        result = subprocess.run(inspect_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            arch = result.stdout.strip()
            print(f"   ✅ Image architecture: {arch}")
            if arch != "amd64":
                print(
                    f"   ⚠️  WARNING: Architecture {arch} may not be compatible with Heroku"
                )

        # Push with retries and better error handling
        print("\n4. Pushing to Heroku Container Registry...")
        push_cmd = ["docker", "push", f"registry.heroku.com/{app_name}/web"]

        for attempt in range(3):  # Try 3 times
            print(f"   Attempt {attempt + 1}/3...")
            push_result = subprocess.run(push_cmd, capture_output=True, text=True)

            if push_result.returncode == 0:
                print("   ✅ Push completed successfully")
                break
            else:
                print(f"   ❌ Push attempt {attempt + 1} failed")
                if "unsupported" in push_result.stderr:
                    print("   ERROR: 'unsupported' error from registry")
                    print(
                        "   This usually indicates architecture mismatch or registry issues"
                    )

                if attempt == 2:  # Last attempt
                    print("   All push attempts failed. Error details:")
                    print("   STDOUT:", push_result.stdout)
                    print("   STDERR:", push_result.stderr)
                    print("\n🔧 Troubleshooting suggestions:")
                    print("   1. Try: heroku container:push web --app", app_name)
                    print("   2. Check Heroku status: https://status.heroku.com")
                    print("   3. Verify app exists: heroku apps:info --app", app_name)
                    print("   4. Try recreating the app with container stack:")
                    print(f"      heroku apps:create {app_name} --stack container")
                    sys.exit(1)

                import time

                time.sleep(2)  # Wait before retry

        # Release the image using Heroku API
        print("\n5. Creating release via Heroku API...")

        # Get image ID
        inspect_cmd = [
            "docker",
            "inspect",
            f"registry.heroku.com/{app_name}/web",
            "--format",
            "{{.Id}}",
        ]
        image_result = subprocess.run(inspect_cmd, capture_output=True, text=True)
        if image_result.returncode != 0:
            print("ERROR: Failed to get image ID")
            sys.exit(1)

        image_id = image_result.stdout.strip()
        print(f"   Image ID: {image_id}")

        # Create release via API
        release_cmd = [
            "curl",
            "-n",
            "-X",
            "PATCH",
            f"https://api.heroku.com/apps/{app_name}/formation",
            "-H",
            "Content-Type: application/json",
            "-H",
            "Accept: application/vnd.heroku+json; version=3.docker-releases",
            "-H",
            f"Authorization: Bearer {api_key}",
            "-d",
            f'{{"updates":[{{"type":"web","docker_image":"{image_id}"}}]}}',
        ]

        release_result = subprocess.run(release_cmd, capture_output=True, text=True)
        if release_result.returncode != 0:
            print("ERROR: Heroku release failed")
            print("STDOUT:", release_result.stdout)
            print("STDERR:", release_result.stderr)
            sys.exit(1)

        print("   ✅ Release completed successfully")
        print(f"\n🎉 Successfully deployed to Heroku app: {app_name}")
        print(f"   URL: https://{app_name}.herokuapp.com")

    except Exception as e:
        print(f"ERROR: Manual deploy failed: {e}")
        sys.exit(1)


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
    if args.name == "deploy-heroku":
        deploy_to_heroku()
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
