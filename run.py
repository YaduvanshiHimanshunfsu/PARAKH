import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

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

One command runs the whole project. This script:

  1. checks the Python and Node dependencies,
  2. prepares the database - creating it, seeding the police hierarchy, the
     demo officer accounts and the demo cases, and moving a database from an
     earlier phase safely aside rather than deleting it,
  3. starts the FastAPI backend and the Vite dev server together,
  4. waits until both are actually listening and prints the URLs.

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


def run_command(command, cwd=None, prefix="", extra_env=None):
    """Run a command and stream its output, unbuffered.

    Streaming matters: a startup failure (a stale database, a missing package)
    prints to the child's stdout, and if that is buffered the launcher looks
    like it is working while nothing is listening.

    shell=False on Windows: we build an explicit argv list so the OS creates
    the child directly (no intermediate cmd.exe). This means Ctrl+C kills
    the child cleanly instead of leaving an orphan that holds the port.
    """

    environment = dict(os.environ, PYTHONUNBUFFERED="1", **(extra_env or {}))

    # On Windows, shell=True inserts a hidden cmd.exe between this process and
    # the real child. When the launcher exits, cmd.exe dies but the grandchild
    # (uvicorn) survives as an orphan that keeps port 8000 bound. Passing an
    # explicit list with shell=False avoids that entire problem.
    if isinstance(command, str):
        import shlex
        argv = shlex.split(command, posix=(sys.platform != "win32"))
    else:
        argv = command

    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=environment,
        shell=False,
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


def prepare_database(venv_python: str, *, reset: bool, demo_cases: bool) -> bool:
    """Create, heal and seed the database before the servers start.

    Run as a subprocess with the virtual environment's interpreter, because
    run.py itself may be executed by a different Python that cannot import the
    application's dependencies.
    """

    print("[Orchestrator] Preparing the database...", flush=True)
    command = [venv_python, "scripts/prepare_demo.py"]
    if reset:
        command.append("--reset")
    if not demo_cases:
        command.append("--no-demo-cases")

    result = subprocess.run(
        command,
        env=dict(os.environ, PYTHONUNBUFFERED="1"),
        capture_output=True,
        text=True,
    )
    for line in (result.stdout or "").splitlines():
        print(f"  {line}", flush=True)
    if result.returncode != 0:
        print("[Orchestrator] The database could not be prepared:", flush=True)
        for line in (result.stderr or "").strip().splitlines()[-12:]:
            print(f"  {line}", flush=True)
        return False
    return True


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


def backend_is_ours(host: str, port: int) -> bool:
    """Confirm the thing on this port is a PARAKH backend, not something else.

    A TCP connect only proves *something* is listening. If a stale server from
    an earlier run still holds the port, the new one cannot bind and dies,
    while a socket check happily reports success - against the wrong database.
    """

    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/v1/health", timeout=2) as response:
            body = json.loads(response.read().decode())
        return body.get("status") == "ok" and "offline_fallback_enabled" in body
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return False


def _pid_on_port(port: int) -> int | None:
    """Return the PID of the process listening on *port*, or None.

    Prefers PowerShell Get-NetTCPConnection (reliable, no string parsing);
    falls back to netstat for environments without that cmdlet.
    """
    # PowerShell – most reliable on modern Windows
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                f"(Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue"
                f" | Select-Object -First 1 -ExpandProperty OwningProcess)",
            ],
            capture_output=True, text=True, timeout=6,
        )
        pid_str = result.stdout.strip()
        if pid_str and pid_str.isdigit():
            return int(pid_str)
    except Exception:
        pass

    # Fallback: parse netstat output
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    try:
                        return int(parts[-1])
                    except ValueError:
                        pass
    except Exception:
        pass
    return None


def _find_uvicorn_pids() -> list[int]:
    """Find PIDs of all Python processes running uvicorn, via WMI.

    This is the reliable way to find orphan uvicorn processes: we search
    by command-line content rather than by port→PID (which is broken when
    the socket owner PID has been recycled by the OS).
    """
    if sys.platform != "win32":
        return []
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                "Get-WmiObject Win32_Process -Filter \"Name='python.exe'\" | "
                "Where-Object { $_.CommandLine -like '*uvicorn*' } | "
                "Select-Object -ExpandProperty ProcessId",
            ],
            capture_output=True, text=True, timeout=8,
        )
        pids = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if line.isdigit():
                pids.append(int(line))
        return pids
    except Exception:
        return []


def _kill_pid(pid: int) -> bool:
    """Kill a process by PID.  Returns True when the kill was sent (not
    necessarily when the socket is released)."""

    if sys.platform != "win32":
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return True
        except ProcessLookupError:
            return True  # Already gone – that is fine.
        except Exception as exc:
            print(f"[Orchestrator] Could not kill PID {pid}: {exc}", flush=True)
            return False

    # Windows: try Stop-Process first (handles protected processes better than
    # taskkill, and returns 0 when the process no longer exists).
    ps_result = subprocess.run(
        [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue",
        ],
        capture_output=True, text=True,
    )
    if ps_result.returncode == 0:
        return True

    # Fallback: taskkill /F /PID
    tk_result = subprocess.run(
        ["taskkill", "/F", "/PID", str(pid)],
        capture_output=True, text=True,
    )
    # Exit 128 = process already gone – treat as success.
    if tk_result.returncode in (0, 128):
        return True

    print(
        f"[Orchestrator] Could not kill PID {pid} "
        f"(taskkill exit {tk_result.returncode}: {tk_result.stderr.strip() or tk_result.stdout.strip()}).\n"
        "[Orchestrator] Try running this terminal as Administrator.",
        flush=True,
    )
    return False


def _kill_by_port(port: int) -> bool:
    """Nuclear option: kill every process listening on *port* via PowerShell."""
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue"
                f" | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}",
            ],
            capture_output=True, text=True, timeout=8,
        )
        return result.returncode == 0
    except Exception as exc:
        print(f"[Orchestrator] Kill-by-port failed: {exc}", flush=True)
        return False


def check_port_free(name: str, host: str, port: int) -> bool:
    """Kill a stale PARAKH process if it owns the port; refuse for anything else."""

    if not port_is_open(host, port):
        return True

    is_ours = name == "Backend" and backend_is_ours(host, port)

    if is_ours:
        # Find the REAL uvicorn process by command-line search, not by port→PID.
        # Port→PID (netstat / Get-NetTCPConnection) is unreliable: on Windows,
        # the socket creator PID can be recycled while uvicorn's orphan keeps
        # serving, so the PID in netstat points to a dead or unrelated process.
        uvicorn_pids = _find_uvicorn_pids()
        port_pid = _pid_on_port(port)

        # Build a human-readable label for the prompt.
        if uvicorn_pids:
            pid_label = f" (uvicorn PID{'s' if len(uvicorn_pids) > 1 else ''}: {', '.join(map(str, uvicorn_pids))})"
        elif port_pid:
            pid_label = f" (port owner PID: {port_pid})"
        else:
            pid_label = ""

        print(
            f"\n[Orchestrator] A stale PARAKH backend{pid_label} is still holding port {port}.",
            flush=True,
        )
        answer = input("[Orchestrator] Kill it and restart? [Y/n]: ").strip().lower()
        if answer not in ("", "y", "yes"):
            print(
                f"[Orchestrator] Exiting. Use --backend-port {port + 1} to run on a different port.",
                flush=True,
            )
            return False

        # Kill by uvicorn commandline first (most reliable).
        killed_any = False
        for pid in uvicorn_pids:
            if _kill_pid(pid):
                killed_any = True
                print(f"[Orchestrator] Killed uvicorn PID {pid}.", flush=True)

        # Also attempt kill by port-owner PID as belt-and-suspenders.
        if port_pid and port_pid not in uvicorn_pids:
            if _kill_pid(port_pid):
                killed_any = True

        # Last resort: PowerShell kill-by-port.
        if not killed_any:
            print("[Orchestrator] Trying kill-by-port as last resort...", flush=True)
            _kill_by_port(port)

        # Give the OS up to 15 s to release the socket.
        for _ in range(30):
            time.sleep(0.5)
            if not port_is_open(host, port):
                print(f"[Orchestrator] Port {port} is now free. Continuing...", flush=True)
                return True

        print(
            f"[Orchestrator] Port {port} did not release after 15 s.\n"
            f"[Orchestrator] Use a different port:  python run.py --backend-port {port + 1}",
            flush=True,
        )
        return False

    # Port taken by something unrelated to PARAKH.
    print(
        f"\n[Orchestrator] Port {port} is already in use by another process, so {name} cannot start.\n"
        f"[Orchestrator] Close the other process, or pick another port:\n"
        f"    python run.py --{name.lower()}-port {port + 1}\n"
        "[Orchestrator] On Windows, find the owner with:\n"
        f"    netstat -ano | findstr :{port}",
        flush=True,
    )
    return False


def wait_for(name: str, host: str, port: int, seconds: int = 30, verify=None) -> bool:
    """Wait until the service is genuinely answering, not merely listening."""

    deadline = time.time() + seconds
    while time.time() < deadline:
        if port_is_open(host, port) and (verify is None or verify()):
            return True
        time.sleep(0.5)
    print(
        f"\n[Orchestrator] {name} did not come up on port {port} within {seconds}s.\n"
        f"[Orchestrator] Read the [{name}] lines above for the reason.",
        flush=True,
    )
    return False


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the whole PARAKH project: database, backend and frontend."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="start from an empty database (the current one is moved aside, not deleted)",
    )
    parser.add_argument(
        "--no-demo-cases",
        action="store_true",
        help="seed the hierarchy and officer accounts but no demo cases",
    )
    parser.add_argument(
        "--skip-prepare",
        action="store_true",
        help="do not touch the database at all",
    )
    parser.add_argument("--backend-port", type=int, default=BACKEND_PORT, help="FastAPI port")
    parser.add_argument("--frontend-port", type=int, default=FRONTEND_PORT, help="Vite dev-server port")
    return parser.parse_args()


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    args = parse_args()

    print("=" * 70, flush=True)
    print(" PARAKH - local development launcher", flush=True)
    print(" Team Gravity | Rajasthan Police Hackathon 2026 | PS01", flush=True)
    print("=" * 70, flush=True)

    if not os.path.exists("app") or not os.path.exists("frontend"):
        print("Error: run.py must be run from the PARAKH project root (it needs 'app' and 'frontend').")
        sys.exit(1)

    backend_port = args.backend_port
    frontend_port = args.frontend_port
    if not check_port_free("Backend", BACKEND_HOST, backend_port):
        sys.exit(1)
    if not check_port_free("Frontend", "localhost", frontend_port):
        sys.exit(1)

    venv_python = check_backend()
    check_frontend()

    if not args.skip_prepare:
        if not prepare_database(
            venv_python, reset=args.reset, demo_cases=not args.no_demo_cases
        ):
            print(
                "\n[Orchestrator] Stopping: the backend would fail to start.\n"
                "[Orchestrator] If this is a database from an earlier phase, run:\n"
                "    python run.py --reset\n"
                "[Orchestrator] That moves the current database aside with a timestamp; "
                "it does not delete it.",
                flush=True,
            )
            sys.exit(1)

    print("\n[Orchestrator] Starting services...\n", flush=True)

    backend = threading.Thread(
        target=run_command,
        args=(
            [venv_python, "-m", "uvicorn", "app.main:app",
             "--host", BACKEND_HOST, "--port", str(backend_port), "--reload"],
            ".",
            "[Backend]  ",
        ),
        daemon=True,
    )
    backend.start()

    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend = threading.Thread(
        target=run_command,
        args=(
            [npm, "run", "dev", "--", "--port", str(frontend_port), "--strictPort"],
            "frontend",
            "[Frontend] ",
        ),
        # The dev-server proxy must point at the backend we actually started.
        kwargs={"extra_env": {"VITE_API_PROXY_TARGET": f"http://{BACKEND_HOST}:{backend_port}"}},
        daemon=True,
    )
    frontend.start()

    backend_up = wait_for(
        "Backend", BACKEND_HOST, backend_port, verify=lambda: backend_is_ours(BACKEND_HOST, backend_port)
    )
    frontend_up = wait_for("Frontend", "localhost", frontend_port)

    if backend_up and frontend_up:
        print(
            "\n"
            + "=" * 70
            + f"\n  Citizen app     http://localhost:{frontend_port}/"
            + f"\n  Officer console http://localhost:{frontend_port}/investigate/login"
            + f"\n  API docs        http://{BACKEND_HOST}:{backend_port}/docs"
            + "\n\n  Demo officers (password ParakhDemo@2026):"
            + "\n    io.si.sharma  SI        drafts requisitions, cannot approve"
            + "\n    sho.cyber     Inspector station approval, assigns cases"
            + "\n    sp.jaipur     SP        district approval (every freeze needs it)"
            + "\n    io.btp        Inspector Bharatpur - cannot see Jaipur's cases"
            + "\n  Full list: python scripts/seed_demo_officers.py --show"
            + "\n\n  Stop with Ctrl+C."
            + "\n"
            + "=" * 70
            + "\n",
            flush=True,
        )
    elif not backend_up:
        print(
            "[Orchestrator] If the backend reported a schema error, run:\n"
            "    python run.py --reset\n"
            "[Orchestrator] That moves the current database aside with a timestamp.",
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
