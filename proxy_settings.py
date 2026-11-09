import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import aiohttp


@dataclass(frozen=True)
class ProxySettings:
    enabled: bool
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    endpoint: Optional[str] = None


def _read_env_file(env_path: Path) -> dict:
    values = {}
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return values

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].lstrip()
        if "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def load_proxy_settings(env_path: Optional[Path] = None) -> ProxySettings:
    """Load optional proxy settings; process environment takes precedence over .env."""
    env_path = env_path or Path(__file__).resolve().parents[1] / ".env"
    file_values = _read_env_file(env_path)

    def setting(name: str, default: str = "") -> str:
        return os.environ.get(name, file_values.get(name, default)).strip()

    enabled = setting("PROXY_ENABLED", "false").lower() == "true"
    if not enabled:
        return ProxySettings(enabled=False)

    scheme = setting("PROXY_SCHEME", "http").lower()
    if scheme not in {"http", "https"}:
        raise ValueError("PROXY_SCHEME must be either 'http' or 'https'.")

    host = setting("PROXY_HOST")
    port_value = setting("PROXY_PORT")
    username = setting("PROXY_USERNAME")
    password = setting("PROXY_PASSWORD")

    if not host or not port_value:
        raise ValueError("PROXY_HOST and PROXY_PORT are required when proxy is enabled.")
    if bool(username) != bool(password):
        raise ValueError("Set both PROXY_USERNAME and PROXY_PASSWORD, or leave both empty.")

    try:
        port = int(port_value)
    except ValueError as exc:
        raise ValueError("PROXY_PORT must be an integer.") from exc
    if not 1 <= port <= 65535:
        raise ValueError("PROXY_PORT must be between 1 and 65535.")

    url = f"{scheme}://{host}:{port}"
    headers = (
        {"Proxy-Authorization": aiohttp.encode_basic_auth(username, password)}
        if username
        else None
    )
    return ProxySettings(enabled=True, url=url, headers=headers, endpoint=url)
