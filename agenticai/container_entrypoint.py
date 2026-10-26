"""Start the restricted installer as root and the application as UID/GID 1000."""

import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path


def main():
    data = Path(os.environ.get("AGENTICAI_DATA", "/data"))
    data.mkdir(parents=True, exist_ok=True)
    os.chown(data, 1000, 1000)
    for name in (
        "tools",
        "tools/python",
        "tools/npm",
        "runs",
        "tool-tests",
        "installations",
    ):
        path = data / name
        path.mkdir(parents=True, exist_ok=True)
        os.chown(path, 1000, 1000)
    socketdir = Path("/run/agenticai")
    socketdir.mkdir(mode=0o750, exist_ok=True)
    os.chown(socketdir, 0, 1000)
    token = socketdir / "installer.token"
    token.write_text(secrets.token_urlsafe(48))
    os.chown(token, 0, 1000)
    token.chmod(0o640)
    socket = socketdir / "installer.sock"
    socket.unlink(missing_ok=True)
    os.environ.update(
        AGENTICAI_INSTALLER_SOCKET=str(socket),
        AGENTICAI_INSTALLER_TOKEN_FILE=str(token),
        AGENTICAI_CONTAINER="1",
        HOME="/home/studio",
    )
    helper = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "agenticai.installer_helper:app",
            "--uds",
            str(socket),
            "--no-access-log",
        ]
    )

    def stop(*args):
        app.terminate()
        helper.terminate()

    try:
        for _ in range(100):
            if socket.exists():
                break
            if helper.poll() is not None:
                raise RuntimeError("Installer helper failed to start")
            time.sleep(0.05)
        if not socket.exists():
            raise RuntimeError("Installer helper did not create its socket")
        os.chown(socket, 0, 1000)
        socket.chmod(0o660)
        app = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "agenticai",
                "serve",
                "--host",
                "0.0.0.0",
                "--data",
                str(data),
                *sys.argv[1:],
            ],
            user=1000,
            group=1000,
            extra_groups=[],
        )
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        while app.poll() is None:
            if helper.poll() is not None:
                app.terminate()
                raise RuntimeError("Installer helper exited")
            time.sleep(0.25)
        return app.returncode
    finally:
        helper.terminate()
        try:
            helper.wait(timeout=10)
        except subprocess.TimeoutExpired:
            helper.kill()


if __name__ == "__main__":
    raise SystemExit(main())
