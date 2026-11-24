import os
import socket
import subprocess
import sys
import threading
import time

"""
========================================================================
Project Name: PARAKH
Developer   : Himanshu Yadav
Email ID    : himanshu.btmtcs4242906@nfsu.ac.in
Purpose     : Local development launcher for PARAKH

Brief Description:
PARAKH is a cyber-fraud verification and investigation platform built for
Rajasthan Police (PS01). It analyses messages, links, emails, QR codes,
websites and Android apps, explains its verdict in plain Hindi or English,
and turns a case into the legal paperwork an investigation needs.

This script checks the required dependencies, then runs the FastAPI backend
and the Vite dev server together.

For a DEMO, prefer the built frontend served by FastAPI on one port:
    cd frontend && npm run build
    python -m uvicorn app.main:app --port 8000
That path works with Wi-Fi switched off and is what DEMO.md describes.
========================================================================
"""

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173

# Imported by the backend on the very first request. Checking them up front
# turns a confusing runtime traceback into one clear message.
REQUIRED_IMPORTS = (
    "fastapi",
    "uvicorn",
    "pydantic",
    "sqlalchemy",
    "aiosqlite",
    "tldextract",
    "phonenumbers",
    "pyaxmlparser",
    "bs4",
)


def run_command(command, cwd=None, prefix=""):
    """Run a command and stream its output, unbuffered.

    Streaming matters: a startup failure (a stale database, a missing package)
    prints to the child's stdout, and if that is buffered the launcher looks
    like it is working while nothing is listening.
    """

    environment = dict(os.environ, PYTHONUNBUFFERED="1")
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=environment,
        shell=sys.platform == "win32",
    )
    for line in iter(process.stdout.readline, ""):
        print(f"{prefix}{line}", end="", flush=True)
    process.stdout.close()
    return process.wait()


def get_venv_python():
    venv_dir = ".venv"
    if sys.platform == "win32":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def ensure_venv():
    venv_dir = ".venv"
    if not os.path.exists(venv_dir):
        print("[Orchestrator] Creating virtual environment for the backend...", flush=True)
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    return get_venv_python()


def check_backend():
    print("[Orchestrator] Checking backend dependencies...", flush=True)
    venv_python = ensure_venv()
    probe = "; ".join(f"import {name}" for name in REQUIRED_IMPORTS)
    result = subprocess.run([venv_python, "-c", probe], capture_output=True, text=True)
    if result.returncode == 0:
        print("[Orchestrator] Backend dependencies are satisfied.", flush=True)
        return venv_python

    missing = (result.stderr or "").strip().splitlines()
    print(f"[Orchestrator] A required Python package is missing: {missing[-1] if missing else 'unknown'}", flush=True)
    answer = input("Install backend dependencies now? [y/N]: ")
    if answer.strip().lower() == "y":
        subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("[Orchestrator] Backend dependencies installed.", flush=True)
    else:
        print("[Orchestrator] Continuing without installing; the backend will probably fail to start.", flush=True)
    return venv_python


def check_frontend():
    print("[Orchestrator] Checking frontend dependencies...", flush=True)
    if os.path.exists(os.path.join("frontend", "node_modules")):
        print("[Orchestrator] Frontend dependencies are satisfied.", flush=True)
        return
    print("[Orchestrator] frontend/node_modules not found.", flush=True)
    answer = input("Install frontend dependencies now? [y/N]: ")
    if answer.strip().lower() == "y":
        npm = "npm.cmd" if sys.platform == "win32" else "npm"
        subprocess.run([npm, "install"], cwd="frontend", check=True)
        print("[Orchestrator] Frontend dependencies installed.", flush=True)
    else:
        print("[Orchestrator] Continuing without installing; the frontend will probably fail to start.", flush=True)


def port_is_open(host: str, port: int, timeout: float = 0.6) -> bool:
    for family, address in ((socket.AF_INET, (host, port)), (socket.AF_INET6, ("::1", port))):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as probe:
                probe.settimeout(timeout)
                if probe.connect_ex(address) == 0:
                    return True
        except OSError:
            continue
    return False


def wait_for(name: str, host: str, port: int, seconds: int = 25) -> bool:
    """Wait for a service to listen, so a silent failure is reported."""

    deadline = time.time() + seconds
    while time.time() < deadline:
        if port_is_open(host, port):
            return True
        time.sleep(0.5)
    print(
        f"\n[Orchestrator] {name} is not listening on port {port} after {seconds}s.\n"
        f"[Orchestrator] Read the [{name}] lines above for the reason.",
        flush=True,
    )
    return False


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("=" * 70, flush=True)
    print(" PARAKH - local development launcher", flush=True)
    print(" Team Gravity | Rajasthan Police Hackathon 2026 | PS01", flush=True)
    print("=" * 70, flush=True)

    if not os.path.exists("app") or not os.path.exists("frontend"):
        print("Error: run.py must be run from the PARAKH project root (it needs 'app' and 'frontend').")
        sys.exit(1)

    venv_python = check_backend()
    check_frontend()

    print("\n[Orchestrator] Starting services...\n", flush=True)

    backend = threading.Thread(
        target=run_command,
        args=(
            f'"{venv_python}" -m uvicorn app.main:app --host {BACKEND_HOST} --port {BACKEND_PORT} --reload',
            ".",
            "[Backend]  ",
        ),
        daemon=True,
    )
    backend.start()

    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend = threading.Thread(
        target=run_command,
        args=(f"{npm} run dev", "frontend", "[Frontend] "),
        daemon=True,
    )
    frontend.start()

    backend_up = wait_for("Backend", BACKEND_HOST, BACKEND_PORT)
    frontend_up = wait_for("Frontend", "localhost", FRONTEND_PORT)

    if backend_up and frontend_up:
        print(
            "\n"
            + "=" * 70
            + f"\n  Citizen app     http://localhost:{FRONTEND_PORT}/"
            + f"\n  Officer console http://localhost:{FRONTEND_PORT}/investigate/login"
            + f"\n  API docs        http://{BACKEND_HOST}:{BACKEND_PORT}/docs"
            + "\n\n  Demo officer accounts: python scripts/seed_demo_officers.py --show"
            + "\n  Stop with Ctrl+C."
            + "\n"
            + "=" * 70
            + "\n",
            flush=True,
        )
    elif not backend_up:
        # The usual cause is a database file from an earlier phase; the backend
        # now says so explicitly on startup.
        print(
            "[Orchestrator] If the backend reported a schema error, run:\n"
            "    python scripts/reset_demo_db.py --yes\n",
            flush=True,
        )

    try:
        backend.join()
        frontend.join()
    except KeyboardInterrupt:
        print("\n[Orchestrator] Shutting down PARAKH services...", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
