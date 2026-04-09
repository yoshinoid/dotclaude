"""Persistent config store for dotclaude settings.

Location: $XDG_CONFIG_HOME/dotclaude/config.json
         (default: ~/.config/dotclaude/config.json)
File permissions: 0o600 (owner read/write only) to protect API keys.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

_DEFAULT_SERVER_URL = "http://localhost:3000"

# Keys stored in config.json
_KEY_GEMINI_API_KEY = "geminiApiKey"
_KEY_AUTH_TOKEN = "authToken"
_KEY_REFRESH_TOKEN = "refreshToken"
_KEY_SERVER_URL = "serverUrl"


def _resolve_config_path() -> Path:
    """Return the path to the config file."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config else Path.home() / ".config"
    return base / "dotclaude" / "config.json"


def get_server_url() -> str:
    """Return the server URL from env var or stored config."""
    env_url = os.environ.get("DOTCLAUDE_SERVER_URL")
    if env_url:
        return env_url
    config = read_config()
    return config.get(_KEY_SERVER_URL, _DEFAULT_SERVER_URL)  # type: ignore[return-value]


def read_config() -> dict[str, Any]:
    """Read the config file and return it as a dict.

    Returns an empty dict if the file does not exist or cannot be parsed.
    """
    p = _resolve_config_path()
    if not p.exists():
        return {}
    try:
        raw = p.read_text(encoding="utf-8")
        result = json.loads(raw)
        if not isinstance(result, dict):
            return {}
        return result
    except (OSError, json.JSONDecodeError):
        sys.stderr.write(
            f"[dotclaude] Warning: failed to parse config at {p} — ignoring\n"
        )
        return {}


def write_config(config: dict[str, Any]) -> None:
    """Write the config dict to the config file with restricted permissions.

    Creates parent directories with mode 0o700.
    File is written with mode 0o600 to protect stored API keys.
    """
    p = _resolve_config_path()
    # mode 0o700 — prevent other users from listing the config directory
    p.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        p.parent.chmod(0o700)

    content = json.dumps(config, indent=2) + "\n"
    p.write_text(content, encoding="utf-8")

    # mode 0o600 — owner read/write only
    if sys.platform != "win32":
        p.chmod(stat.S_IRUSR | stat.S_IWUSR)


def get_gemini_api_key() -> str | None:
    """Return the Gemini API key. Env var takes priority over stored config."""
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key:
        return env_key
    config = read_config()
    val = config.get(_KEY_GEMINI_API_KEY)
    return str(val) if val is not None else None


def get_config_file_path() -> str:
    """Return the path to the config file as a string."""
    return str(_resolve_config_path())
