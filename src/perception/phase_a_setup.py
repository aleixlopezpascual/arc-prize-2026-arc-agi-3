"""phase_a_setup.py - Setup for Phase A CPU Pre-Exploration Arcade instance.

Connects to Kaggle competition gateway if in competition mode, or initializes
offline arcade using bundled environment files.
"""
from __future__ import annotations

import http.client
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

_GATEWAY_HOST_ALLOWLIST = {"gateway", "localhost", "127.0.0.1"}


def wait_for_gateway(base_url: str, timeout_s: float = 600.0) -> None:
    parts = urlsplit(base_url)
    host = (parts.hostname or "").lower()
    if host not in _GATEWAY_HOST_ALLOWLIST:
        raise RuntimeError(f"Unexpected gateway host {host!r}")
    port = parts.port or (443 if (parts.scheme or "http") == "https" else 80)
    use_tls = (parts.scheme or "http") == "https"
    prefix = (parts.path or "").rstrip("/")
    deadline = time.monotonic() + timeout_s
    last_error = ""
    while time.monotonic() < deadline:
        conn = None
        try:
            conn = (
                http.client.HTTPSConnection(host, port, timeout=10)
                if use_tls
                else http.client.HTTPConnection(host, port, timeout=10)
            )
            conn.request("GET", f"{prefix}/api/games")
            resp = conn.getresponse()
            resp.read()
            if resp.status < 500:
                return
            last_error = f"status {resp.status}"
        except Exception as exc:
            last_error = repr(exc)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        time.sleep(5)
    raise RuntimeError(f"Gateway wait failed: {last_error}")


def explore_arcade(true_submission: bool):
    import arc_agi

    if true_submission:
        base_url = os.environ.get("ARC_BASE_URL", "http://gateway:8001/")
        wait_for_gateway(base_url)
        return arc_agi.Arcade(
            operation_mode=arc_agi.OperationMode.COMPETITION,
            arc_base_url=base_url,
            environments_dir="",
        )

    # Dynamic wheelhouse / env_files resolution
    wheelhouse = next(
        iter(sorted(Path("/kaggle/input").glob("**/arc_agi_3_wheels"))),
        Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels"),
    )
    env_dir = os.getenv("PRE_EXPLORATION_ENV_DIR") or str(
        wheelhouse.parent / "environment_files"
    )
    if not os.path.isdir(env_dir):
        # Fallback to local repo environment files if running locally
        local_env = Path("input/environment_files")
        if local_env.is_dir():
            env_dir = str(local_env.resolve())

    return arc_agi.Arcade(
        operation_mode=arc_agi.OperationMode.OFFLINE,
        environments_dir=env_dir,
    )
