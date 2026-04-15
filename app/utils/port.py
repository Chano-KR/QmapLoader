from __future__ import annotations

import socket


def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def choose_port(primary: int, fallback: int) -> int:
    """Prefer primary; fall back to `fallback` if primary is taken."""
    if is_port_free(primary):
        return primary
    if is_port_free(fallback):
        return fallback
    raise RuntimeError(
        f"Neither port {primary} nor {fallback} is available. "
        "Close the process using these ports and try again."
    )
